from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import ExpireWaitlist
from drlibre.booking.application.ports.outbound import Waitlist
from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class ExpireWaitlistUseCase(ExpireWaitlist):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, waitlist: Waitlist
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._waitlist = waitlist

    def execute(self) -> int:
        now = self._clock.now()
        with self._uow:
            due = self._waitlist.expiring_locked(now)
            for expiring in due:
                entry = expiring.entry
                if entry.status is WaitlistStatus.OFFERED:
                    action, entry = "booking.waitlist_offer_lapsed", entry.back_to_waiting()
                else:
                    action = "booking.waitlist_expired"
                if entry.latest <= now:
                    entry = entry.expired()
                self._waitlist.save(entry)
                self._audit.record(
                    AuditEntry.from_event(
                        actor=None,
                        action=action,
                        entity_type="waitlist_entry",
                        entity_id=entry.id,
                        at=now,
                        metadata={"status": entry.status},
                    )
                )
        return len(due)
