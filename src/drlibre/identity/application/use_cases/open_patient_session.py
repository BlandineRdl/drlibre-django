from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import OpenPatientSession, SignedIn
from drlibre.identity.application.ports.outbound import Sessions, TokenGenerator, Users
from drlibre.identity.domain.session import Session
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class OpenPatientSessionUseCase(OpenPatientSession):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        sessions: Sessions,
        tokens: TokenGenerator,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._tokens = tokens

    def execute(self, *, patient_id: Id, user_agent: str) -> SignedIn:
        user = self._users.get(patient_id)
        if user is None or not user.active:
            raise DomainError(ErrorCode.FORBIDDEN, "Cette réservation ne peut pas être effectuée.")
        at = self._clock.now()
        token = self._tokens.new_token()
        session = Session.after_email_proof(
            token=token, user_id=user.id, user_agent=user_agent, at=at
        )
        with self._uow:
            self._sessions.add(session)
            self._users.save(user.signed_in(at=at))
            self._audit.record(
                AuditEntry.from_event(
                    actor=user.id,
                    action="auth.login_succeeded",
                    entity_type="user",
                    entity_id=user.id,
                    at=at,
                    metadata={"email_domain": user.email.domain},
                )
            )
        return SignedIn(token=token, role=user.role, expires_at=session.expires_at)
