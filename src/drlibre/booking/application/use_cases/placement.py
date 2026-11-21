from collections.abc import Callable
from datetime import datetime, timedelta

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookableClinician,
    BookableType,
    BookingDirectory,
    BookingNotices,
    FreeSlots,
    Holds,
    Patients,
    ScheduleLocks,
    SlotRefresh,
)
from drlibre.booking.application.use_cases.require_patient import refuse_non_patient
from drlibre.booking.domain import booking_rules
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.booking.domain.round_robin import Candidate, rank
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class Placement:
    """The spec 5.2 steps every booking path runs, stopping at the first failure."""

    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: BookingDirectory,
        appointments: Appointments,
        free_slots: FreeSlots,
        slot_refresh: SlotRefresh,
        locks: ScheduleLocks,
        patients: Patients,
        notices: BookingNotices,
        holds: Holds,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._directory = directory
        self._appointments = appointments
        self._free_slots = free_slots
        self._slot_refresh = slot_refresh
        self._locks = locks
        self._patients = patients
        self._notices = notices
        self._holds = holds

    def bookable_type(self, appointment_type_id: Id) -> BookableType:
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None or not kind.active:
            raise DomainError(ErrorCode.NOT_FOUND, "Type de RDV introuvable.")
        return kind

    def clinician_of(self, kind: BookableType, clinician_id: Id) -> BookableClinician:
        clinician = self._directory.clinician(clinician_id)
        if (
            clinician is None
            or not clinician.active
            or clinician.department_id != kind.department_id
        ):
            raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
        return clinician

    def ranked_candidates(self, kind: BookableType, start: datetime) -> tuple[Id, ...]:
        """The clinicians with a free slot at the start, best ranked first; none is refused."""
        free = self._free_slots.candidates_at(kind.id, start)
        # All candidates are locked in one order before ranking, so no two bookings deadlock.
        self._locks.lock_clinicians(free)
        candidates = []
        for clinician_id in free:
            clinician = self._directory.clinician(clinician_id)
            if (
                clinician is not None
                and clinician.active
                and clinician.department_id == kind.department_id
                and clinician.weight > 0
            ):
                candidates.append(
                    Candidate(clinician.id, clinician.weight, clinician.last_assigned_at)
                )
        ranked = rank(tuple(candidates), self._clock.now())
        if not ranked:
            raise DomainError(ErrorCode.NO_CLINICIAN_AVAILABLE, "Aucun praticien disponible.")
        return tuple(candidate.clinician_id for candidate in ranked)

    def first_free[T](self, candidates: tuple[Id, ...], attempt: Callable[[Id], T]) -> T:
        """The first attempt not refused as taken; no_clinician_available when all are."""
        for clinician_id in candidates:
            try:
                return attempt(clinician_id)
            except DomainError as refusal:
                if refusal.code is not ErrorCode.CONFLICT or (
                    "clinician" not in refusal.details.get("resources", [])
                ):
                    raise
        raise DomainError(ErrorCode.NO_CLINICIAN_AVAILABLE, "Aucun praticien disponible.")

    def place(
        self,
        *,
        patient_id: Id,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        source: Source,
        ignoring_hold: Id | None = None,
        reason: str | None = None,
        for_patient: bool = True,
        actor: Id | None = None,
        room_id: Id | None = None,
    ) -> Appointment:
        """Book once every step passes; staff skip patient rules and may name a room."""
        with self._uow:
            self._locks.lock_clinician(clinician_id)
            self._locks.lock_patient(patient_id)
            refuse_non_patient(self._patients, patient_id)
            kind = self.bookable_type(appointment_type_id)
            clinician = self.clinician_of(kind, clinician_id)
            duration = timedelta(minutes=kind.duration_minutes)
            self.refuse_conflicts(
                patient_id, clinician_id, start, start + duration, ignoring_hold=ignoring_hold
            )
            self.refuse_rule_violations(
                patient_id,
                clinician_id,
                kind,
                start,
                ignoring_hold=ignoring_hold,
                for_patient=for_patient,
            )
            end = start + duration
            appointment = Appointment.book(
                patient_id=patient_id,
                clinician_id=clinician_id,
                appointment_type_id=kind.id,
                room_id=(
                    self.room(kind, clinician, start, end)
                    if room_id is None
                    else self.named_room(kind, room_id, start, end)
                ),
                start=start,
                duration=duration,
                source=source,
                reason=reason,
            )
            self._appointments.add(appointment)
            self._notices.booked(appointment)
            self._audit.record(self._booked_entry(appointment, actor or patient_id))
            self._slot_refresh.refresh(clinician_id)
            self._notices.confirmed(appointment)
            return appointment

    def refuse_conflicts(
        self,
        patient_id: Id | None,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        *,
        ignoring_hold: Id | None,
        excluding: Id | None = None,
    ) -> None:
        """conflict when another active appointment than the excluded, or an open hold, is there."""
        if patient_id is None:
            resources = (
                ("clinician",)
                if self._appointments.clinician_busy(clinician_id, start, end)
                else ()
            )
        else:
            resources = self._appointments.conflicting_resources(
                clinician_id=clinician_id,
                patient_id=patient_id,
                start=start,
                end=end,
                excluding=excluding,
            )
        held = self._holds.held(
            clinician_id, start, end, at=self._clock.now(), excluding=ignoring_hold
        )
        if held and "clinician" not in resources:
            resources = ("clinician", *resources)
        if resources:
            raise DomainError(
                ErrorCode.CONFLICT,
                "Un rendez-vous actif occupe déjà ce créneau.",
                {"resources": list(resources)},
            )

    def refuse_rule_violations(
        self,
        patient_id: Id | None,
        clinician_id: Id,
        kind: BookableType,
        start: datetime,
        *,
        ignoring_hold: Id | None,
        for_patient: bool = True,
    ) -> None:
        now = self._clock.now()
        broken = booking_rules.violations(
            for_patient=for_patient,
            start=start,
            now=now,
            type_online=kind.bookable_online,
            open_online_count=(
                self._appointments.open_online_count(patient_id, now)
                if for_patient and patient_id is not None
                else 0
            ),
            is_free_slot=self._free_slots.is_free(
                clinician_id, kind.id, start, ignoring_hold=ignoring_hold
            ),
        )
        if broken:
            raise DomainError(
                ErrorCode.RULE_VIOLATION,
                "La réservation enfreint une règle.",
                {"rules": [rule.value for rule in broken]},
            )

    def room(
        self,
        kind: BookableType,
        clinician: BookableClinician,
        start: datetime,
        end: datetime,
        *,
        current: Id | None = None,
        excluding: Id | None = None,
    ) -> Id | None:
        """The current room, else the default, else the first free; locks the department's rooms."""
        if not kind.needs_room:
            return None
        self._locks.lock_rooms(kind.department_id)
        rooms = self._directory.rooms(kind.department_id)
        preferred = (current, clinician.default_room_id)
        order = tuple(dict.fromkeys((*(r for r in preferred if r in rooms), *rooms)))
        busy = self._appointments.busy_rooms(order, start, end, excluding)
        for room_id in order:
            if room_id not in busy:
                return room_id
        raise DomainError(ErrorCode.NO_ROOM_AVAILABLE, "Aucune salle libre à cette heure.")

    def named_room(self, kind: BookableType, room_id: Id, start: datetime, end: datetime) -> Id:
        """The named active room of the type's department; not_found, else conflict when taken."""
        if not kind.needs_room:
            raise invalid_field("room", "Ce type de rendez-vous ne prend pas de salle.")
        self._locks.lock_rooms(kind.department_id)
        if room_id not in self._directory.rooms(kind.department_id):
            raise DomainError(ErrorCode.NOT_FOUND, "Salle introuvable.")
        if self._appointments.busy_rooms((room_id,), start, end):
            raise DomainError(
                ErrorCode.CONFLICT,
                "Un rendez-vous actif occupe déjà cette salle.",
                {"resources": ["room"]},
            )
        return room_id

    def _booked_entry(self, appointment: Appointment, actor: Id) -> AuditEntry:
        metadata: dict[str, object] = {
            "clinician_id": appointment.clinician_id,
            "appointment_type_id": appointment.appointment_type_id,
            "source": appointment.source,
        }
        if appointment.room_id is not None:
            metadata["room_id"] = appointment.room_id
        domain = self._patients.email_domain_of(appointment.patient_id)
        if domain is not None:
            metadata["email_domain"] = domain
        return AuditEntry.from_event(
            actor=actor,
            action="booking.appointment_booked",
            entity_type="appointment",
            entity_id=appointment.id,
            at=self._clock.now(),
            metadata=metadata,
        )
