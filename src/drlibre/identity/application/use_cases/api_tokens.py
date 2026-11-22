from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import (
    AuthenticateToken,
    Identity,
    IssueApiToken,
    RevokeApiTokens,
)
from drlibre.identity.application.ports.outbound import ApiTokens, TokenGenerator, Users
from drlibre.identity.domain.api_token import ApiToken
from drlibre.identity.domain.session import hash_token
from drlibre.identity.domain.user import Email, User
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.unit_of_work import UnitOfWork

UNKNOWN_USER = "Aucun utilisateur actif avec cet email."


def _active_user(users: Users, email: str) -> User:
    user = users.by_email(Email.parse(email))
    if user is None or not user.active:
        raise DomainError(ErrorCode.NOT_FOUND, UNKNOWN_USER)
    return user


class IssueApiTokenUseCase(IssueApiToken):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        api_tokens: ApiTokens,
        tokens: TokenGenerator,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._api_tokens = api_tokens
        self._tokens = tokens

    def execute(self, *, user_email: str, label: str, days: int = 90) -> str:
        at = self._clock.now()
        with self._uow:
            user = _active_user(self._users, user_email)
            raw = self._tokens.new_token()
            token = ApiToken.issue(token=raw, user_id=user.id, label=label, days=days, at=at)
            self._api_tokens.add(token)
            self._audit.record(
                AuditEntry.from_event(
                    actor=None,
                    action="identity.api_token_issued",
                    entity_type="api_token",
                    entity_id=token.id,
                    at=at,
                    metadata={"user": user.id},
                )
            )
        return raw


class RevokeApiTokensUseCase(RevokeApiTokens):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, users: Users, api_tokens: ApiTokens
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._api_tokens = api_tokens

    def execute(self, *, user_email: str) -> int:
        with self._uow:
            user = self._users.by_email(Email.parse(user_email))
            if user is None:
                raise DomainError(ErrorCode.NOT_FOUND, UNKNOWN_USER)
            count = self._api_tokens.delete_for_user(user.id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=None,
                    action="identity.api_tokens_revoked",
                    entity_type="user",
                    entity_id=user.id,
                    at=self._clock.now(),
                    metadata={"count": count},
                )
            )
        return count


class AuthenticateTokenUseCase(AuthenticateToken):
    def __init__(self, *, clock: Clock, users: Users, api_tokens: ApiTokens) -> None:
        self._clock = clock
        self._users = users
        self._api_tokens = api_tokens

    def execute(self, *, token: str) -> Identity | None:
        found = self._api_tokens.by_token_hash(hash_token(token))
        if found is None or found.is_expired(at=self._clock.now()):
            return None
        user = self._users.get(found.user_id)
        if user is None or not user.active:
            return None
        return Identity(
            user_id=user.id,
            role=user.role,
            full_name=user.full_name,
            has_password=user.has_password,
            must_change_password=user.must_change_password,
            session_expires_at=found.expires_at,
            session_renewed=False,
        )
