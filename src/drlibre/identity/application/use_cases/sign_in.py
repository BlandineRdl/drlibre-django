from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import SignedIn, SignIn
from drlibre.identity.application.ports.outbound import (
    FailedSignIns,
    PasswordHasher,
    Sessions,
    TokenGenerator,
    Users,
)
from drlibre.identity.domain.lockout import LOCKOUT_WINDOW, is_locked
from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import Email
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork

BAD_CREDENTIALS = "Email ou mot de passe incorrect."
LOCKED = "Trop de tentatives pour cette adresse. Réessayez dans 15 minutes."


class SignInUseCase(SignIn):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        sessions: Sessions,
        hasher: PasswordHasher,
        failures: FailedSignIns,
        tokens: TokenGenerator,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._failures = failures
        self._tokens = tokens

    def execute(self, *, email: str, password: str, user_agent: str) -> SignedIn:
        at = self._clock.now()
        try:
            address = Email.parse(email)
        except DomainError:
            self._hasher.verify(password, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, BAD_CREDENTIALS) from None
        if is_locked(failures=self._failures.count_since(address, since=at - LOCKOUT_WINDOW)):
            self._audit_alone("auth.login_locked", address, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, LOCKED)
        user = self._users.by_email(address)
        hashed = user.password_hash if user else None
        verified = self._hasher.verify(password, hashed)
        if user is None or not verified or not user.active:
            self._failures.record(address, at=at)
            self._audit_alone("auth.login_failed", address, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, BAD_CREDENTIALS)
        self._failures.clear(address)
        token = self._tokens.new_token()
        session = Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent=user_agent, at=at
        )
        with self._uow:
            self._sessions.add(session)
            self._users.save(user.signed_in(at=at))
            self._audit.record(self._entry("auth.login_succeeded", address, user.id))
        return SignedIn(token=token, role=user.role, expires_at=session.expires_at)

    def _audit_alone(self, action: str, address: Email, user_id: Id | None) -> None:
        # A refusal raises after its own committed audit entry.
        with self._uow:
            self._audit.record(self._entry(action, address, user_id))

    def _entry(self, action: str, address: Email, user_id: Id | None) -> AuditEntry:
        return AuditEntry.from_event(
            actor=user_id,
            action=action,
            entity_type="user",
            entity_id=user_id,
            at=self._clock.now(),
            metadata={"email_domain": address.domain},
        )
