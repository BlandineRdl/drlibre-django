from datetime import datetime

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
from drlibre.shared_kernel.rate_limit import HOURLY
from drlibre.shared_kernel.unit_of_work import UnitOfWork

BAD_CREDENTIALS = "Email ou mot de passe incorrect."
LOCKED = "Trop de tentatives pour cette adresse. Réessayez dans 15 minutes."
NETWORK_LOCKED = "Trop de tentatives depuis ce réseau. Réessayez plus tard."


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
        network_hourly_limit: int,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._failures = failures
        self._tokens = tokens
        self._network_limit = network_hourly_limit

    def execute(self, *, email: str, password: str, user_agent: str, network: str) -> SignedIn:
        at = self._clock.now()
        try:
            address = Email.parse(email)
        except DomainError:
            self._hasher.verify(password, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, BAD_CREDENTIALS) from None
        by_email, by_network = f"email:{address.value}", f"network:{network}"
        self._refuse_if_locked(address, by_email, by_network, at=at, counting=0)
        # Each try is a failure until the password checks, so concurrent tries never pass a limit.
        tries = {s: self._failures.record(s, at=at) for s in (by_email, by_network)}
        try:
            self._refuse_if_locked(address, by_email, by_network, at=at, counting=1)
        except DomainError:
            for subject, failure in tries.items():
                self._failures.forget(subject, failure)
            raise
        user = self._users.by_email(address)
        hashed = user.password_hash if user else None
        verified = self._hasher.verify(password, hashed)
        if user is None or not verified or not user.active:
            self._audit_alone("auth.login_failed", address, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, BAD_CREDENTIALS)
        self._failures.clear(by_email)
        self._failures.forget(by_network, tries[by_network])
        token = self._tokens.new_token()
        session = Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent=user_agent, at=at
        )
        with self._uow:
            self._sessions.add(session)
            self._users.save(user.signed_in(at=at))
            self._audit.record(self._entry("auth.login_succeeded", address, user.id))
        return SignedIn(token=token, role=user.role, expires_at=session.expires_at)

    def _refuse_if_locked(
        self, address: Email, by_email: str, by_network: str, *, at: datetime, counting: int
    ) -> None:
        """Refuse once a limit is reached, not counting the `counting` tries already recorded."""
        failures = self._failures.count_since(by_email, since=at - LOCKOUT_WINDOW) - counting
        if is_locked(failures=failures):
            self._audit_alone("auth.login_locked", address, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, LOCKED)
        from_network = self._failures.count_since(by_network, since=at - HOURLY) - counting
        if from_network >= self._network_limit:
            self._audit_alone("auth.login_locked", address, None)
            raise DomainError(ErrorCode.UNAUTHENTICATED, NETWORK_LOCKED)

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
