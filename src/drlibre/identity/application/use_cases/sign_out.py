from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import SignOut
from drlibre.identity.application.ports.outbound import Sessions
from drlibre.identity.domain.session import hash_token
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class SignOutUseCase(SignOut):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, sessions: Sessions
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._sessions = sessions

    def execute(self, *, token: str) -> None:
        session = self._sessions.by_token_hash(hash_token(token))
        if session is None:
            return
        with self._uow:
            self._sessions.delete(session.id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=session.user_id,
                    action="auth.logout",
                    entity_type="session",
                    entity_id=session.id,
                    at=self._clock.now(),
                )
            )
