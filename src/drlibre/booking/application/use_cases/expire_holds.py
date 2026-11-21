from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import ExpireHolds
from drlibre.booking.application.ports.outbound import Holds, VerificationCodes
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class ExpireHoldsUseCase(ExpireHolds):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        holds: Holds,
        codes: VerificationCodes,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._holds = holds
        self._codes = codes

    def execute(self) -> int:
        at = self._clock.now()
        with self._uow:
            expired = self._holds.expired(at)
            for hold in expired:
                self._codes.delete_for_hold(hold.id)
                self._holds.delete(hold.id)
                self._audit.record(
                    AuditEntry.from_event(
                        actor=None,
                        action="booking.hold_expired",
                        entity_type="booking_hold",
                        entity_id=hold.id,
                        at=at,
                        metadata={"email_domain": hold.details.email_domain},
                    )
                )
        return len(expired)
