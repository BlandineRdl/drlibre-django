from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import Appointment, CancelAppointment
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingDirectory,
    BookingNotices,
    ScheduleLocks,
    SlotRefresh,
    Staff,
)
from drlibre.booking.application.use_cases.actor_scope import (
    actor_scope,
    locked_scoped_appointment,
)
from drlibre.booking.application.use_cases.waitlist_offers import WaitlistOffers
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
        directory: BookingDirectory,
        staff: Staff,
        locks: ScheduleLocks,
        slot_refresh: SlotRefresh,
        notices: BookingNotices,
        offers: WaitlistOffers,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._appointments = appointments
        self._directory = directory
        self._staff = staff
        self._locks = locks
        self._slot_refresh = slot_refresh
        self._notices = notices
        self._offers = offers

    def execute(self, *, appointment_id: Id, actor_id: Id, reason: str) -> Appointment:
        with self._uow:
            scope = actor_scope(self._directory, self._staff, actor_id)
            current = locked_scoped_appointment(
                scope, self._appointments, self._locks, appointment_id
            )
            now = self._clock.now()
            cancelled = current.cancelled(at=now, reason=reason)
            # The 24 hour window binds patients only.
            broken = (
                booking_rules.cancel_violations(start=current.start, now=now)
                if scope.is_patient
                else ()
            )
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
                    actor=actor_id,
                    action="booking.appointment_cancelled",
                    entity_type="appointment",
                    entity_id=cancelled.id,
                    at=now,
                    metadata={"clinician_id": cancelled.clinician_id},
                )
            )
            self._offers.offer_freed(cancelled)
            self._notices.cancelled(cancelled)
            return cancelled
