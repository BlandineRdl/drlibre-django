from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import AcceptWaitlistOffer, Appointment
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingNotices,
    Patients,
    ScheduleLocks,
    Staff,
    Waitlist,
)
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.application.use_cases.require_patient import refuse_non_patient
from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class AcceptWaitlistOfferUseCase(AcceptWaitlistOffer):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        placement: Placement,
        appointments: Appointments,
        locks: ScheduleLocks,
        patients: Patients,
        staff: Staff,
        waitlist: Waitlist,
        notices: BookingNotices,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._placement = placement
        self._appointments = appointments
        self._locks = locks
        self._patients = patients
        self._staff = staff
        self._waitlist = waitlist
        self._notices = notices

    def execute(self, *, actor_id: Id, entry_id: Id) -> Appointment:
        entry = self._waitlist.get(entry_id)
        if entry is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Entrée d'attente introuvable.")
        for_patient = actor_id == entry.patient_id
        if for_patient:
            refuse_non_patient(self._patients, actor_id)
        elif not self._staff.is_admin(actor_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Cette entrée appartient à un autre patient.")
        freed = self._offered(entry)
        with self._uow:
            self._locks.lock_clinician(freed.clinician_id)
            self._locks.lock_patient(entry.patient_id)
            # Read again under the locks, so an offer lapsed or accepted meanwhile is seen.
            current = self._waitlist.get_locked(entry_id)
            if current is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Entrée d'attente introuvable.")
            if current.status is not WaitlistStatus.OFFERED:
                raise _not_offered(current)
            if current.offered_appointment_id != freed.id:
                raise DomainError(
                    ErrorCode.CONFLICT,
                    "L'offre a changé entre-temps.",
                    {"resources": ["waitlist_entry"]},
                )
            outcome = self._place_or_lose(current, freed, actor_id, for_patient=for_patient)
        if isinstance(outcome, DomainError):
            raise outcome
        return outcome

    def _offered(self, entry: WaitlistEntry) -> Appointment:
        offered = entry.offered_appointment_id
        freed = self._appointments.get(offered) if offered else None
        if entry.status is not WaitlistStatus.OFFERED or freed is None:
            raise _not_offered(entry)
        return freed

    def _place_or_lose(
        self, entry: WaitlistEntry, freed: Appointment, actor_id: Id, *, for_patient: bool
    ) -> Appointment | DomainError:
        """The booked appointment, or the conflict that put the entry back to WAITING."""
        source = Source.ONLINE if for_patient else Source.STAFF
        try:
            appointment = self._placement.place(
                patient_id=entry.patient_id,
                clinician_id=freed.clinician_id,
                appointment_type_id=freed.appointment_type_id,
                start=freed.start,
                source=source,
                actor_id=actor_id,
                for_patient=for_patient,
                announce=False,
            )
        except DomainError as refusal:
            if refusal.code is not ErrorCode.CONFLICT:
                raise
            self._waitlist.save(entry.back_to_waiting())
            self._record(
                actor_id, "booking.waitlist_offer_lost", entry, {"appointment_id": freed.id}
            )
            return refusal
        self._waitlist.save(entry.booked())
        self._record(
            actor_id,
            "booking.waitlist_accepted",
            entry,
            {"appointment_id": appointment.id, "source": source},
        )
        self._notices.waitlist_booked(appointment)
        return appointment

    def _record(
        self, actor_id: Id, action: str, entry: WaitlistEntry, metadata: dict[str, object]
    ) -> None:
        self._audit.record(
            AuditEntry.from_event(
                actor=actor_id,
                action=action,
                entity_type="waitlist_entry",
                entity_id=entry.id,
                at=self._clock.now(),
                metadata=metadata,
            )
        )


def _not_offered(entry: WaitlistEntry) -> DomainError:
    return DomainError(
        ErrorCode.INVALID_TRANSITION,
        "Seule une entrée proposée s'accepte.",
        {"status": entry.status.value},
    )
