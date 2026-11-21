from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import JoinWaitlist, WaitlistEntry
from drlibre.booking.application.ports.outbound import Patients, Staff, Waitlist
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.application.use_cases.require_patient import refuse_non_patient
from drlibre.booking.domain.booking_rules import BookingRule
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class JoinWaitlistUseCase(JoinWaitlist):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        placement: Placement,
        patients: Patients,
        staff: Staff,
        waitlist: Waitlist,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._placement = placement
        self._patients = patients
        self._staff = staff
        self._waitlist = waitlist

    def execute(
        self,
        *,
        actor_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        from_date: date,
        to_date: date,
        patient_email: str | None,
    ) -> WaitlistEntry:
        with self._uow:
            patient_id = self._patient(actor_id, patient_email)
            kind = self._placement.bookable_type(appointment_type_id)
            if clinician_id is not None:
                self._placement.clinician_of(kind, clinician_id)
            if patient_email is None and not kind.bookable_online:
                raise DomainError(
                    ErrorCode.RULE_VIOLATION,
                    "Ce type de RDV ne se réserve pas en ligne.",
                    {"rules": [BookingRule.TYPE_NOT_BOOKABLE_ONLINE.value]},
                )
            now = self._clock.now()
            zone = ZoneInfo(kind.time_zone)
            if to_date < from_date or to_date < now.astimezone(zone).date():
                raise invalid_field(
                    "to_date", "Choisissez une date à venir, après la date de début."
                )
            entry = WaitlistEntry.join(
                patient_id=patient_id,
                appointment_type_id=kind.id,
                clinician_id=clinician_id,
                earliest=_midnight(from_date, zone),
                latest=_midnight(to_date + timedelta(days=1), zone),
                at=now,
            )
            self._waitlist.add(entry)
            preferred = {"clinician_id": clinician_id} if clinician_id else {}
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor_id,
                    action="booking.waitlist_joined",
                    entity_type="waitlist_entry",
                    entity_id=entry.id,
                    at=now,
                    metadata={"appointment_type_id": kind.id, **preferred},
                )
            )
            return entry

    def _patient(self, actor_id: Id, patient_email: str | None) -> Id:
        """The actor for themself, or the emailed active patient when the actor is an admin."""
        if patient_email is None:
            refuse_non_patient(self._patients, actor_id)
            return actor_id
        if not self._staff.is_admin(actor_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Seul un admin inscrit un autre patient.")
        found = self._patients.active_patient_by_email(patient_email)
        if found is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Patient introuvable.")
        return found


def _midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time(), zone)
