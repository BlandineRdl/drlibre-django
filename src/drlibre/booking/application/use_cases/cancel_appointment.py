from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import Appointment, CancelAppointment
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingNotices,
    ScheduleLocks,
    SlotRefresh,
)
from drlibre.booking.application.use_cases.view_appointment import own_appointment
from drlibre.booking.domain import booking_rules
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class CancelAppointmentUseCase(CancelAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        appointments: Appointments,
        locks: ScheduleLocks,
        slot_refresh: SlotRefresh,
        notices: BookingNotices,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._appointments = appointments
        self._locks = locks
        self._slot_refresh = slot_refresh
        self._notices = notices

    def execute(self, *, appointment_id: Id, patient_id: Id, reason: str) -> Appointment:
        with self._uow:
            found = own_appointment(self._appointments, appointment_id, patient_id)
            self._locks.lock_clinician(found.clinician_id)
            self._locks.lock_patient(found.patient_id)
            # Read again under the locks, so a change committed meanwhile is seen.
            current = own_appointment(self._appointments, appointment_id, patient_id)
            now = self._clock.now()
            cancelled = current.cancelled(at=now, reason=reason)
            broken = booking_rules.cancel_violations(start=current.start, now=now)
            if broken:
                raise DomainError(
                    ErrorCode.RULE_VIOLATION,
                    "L'annulation enfreint une règle.",
                    {"rules": [rule.value for rule in broken]},
                )
            self._appointments.save(cancelled)
            self._slot_refresh.refresh(cancelled.clinician_id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=patient_id,
                    action="booking.appointment_cancelled",
                    entity_type="appointment",
                    entity_id=cancelled.id,
                    at=now,
                    metadata={"clinician_id": cancelled.clinician_id},
                )
            )
            self._notices.cancelled(cancelled)
            return cancelled
