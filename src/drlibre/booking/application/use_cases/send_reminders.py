from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import SendReminders
from drlibre.booking.application.ports.outbound import Appointments, BookingNotices
from drlibre.shared_kernel.booking_policy import REMINDER_WINDOW
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class SendRemindersUseCase(SendReminders):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        appointments: Appointments,
        notices: BookingNotices,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._appointments = appointments
        self._notices = notices

    def execute(self) -> int:
        now = self._clock.now()
        with self._uow:
            due = self._appointments.booked_starting(now, now + REMINDER_WINDOW)
            # The unique reminder index still refuses a reminder a concurrent run just wrote.
            done = self._notices.already_reminded(frozenset(a.id for a in due))
            sent = sum(1 for a in due if a.id not in done and self._notices.reminded(a))
            if sent:
                self._audit.record(
                    AuditEntry.from_event(
                        actor=None,
                        action="booking.reminders_sent",
                        entity_type="appointment",
                        entity_id=None,
                        at=now,
                        metadata={"count": sent},
                    )
                )
        return sent
