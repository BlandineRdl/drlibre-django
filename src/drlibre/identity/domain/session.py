import dataclasses
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id

ADMIN_LIFETIME = timedelta(hours=12)
PASSWORD_LIFETIME = timedelta(days=7)
EMAIL_PROOF_LIFETIME = timedelta(hours=24)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Session:
    id: Id
    token_hash: str
    user_id: Id
    expires_at: datetime
    lifetime: timedelta
    extendable: bool
    user_agent: str

    @classmethod
    def after_password(
        cls, *, token: str, user_id: Id, role: Role, user_agent: str, at: datetime
    ) -> "Session":
        lifetime = ADMIN_LIFETIME if role is Role.ADMIN else PASSWORD_LIFETIME
        return cls(
            id=Id(),
            token_hash=hash_token(token),
            user_id=user_id,
            expires_at=at + lifetime,
            lifetime=lifetime,
            extendable=True,
            user_agent=user_agent[:300],
        )

    @classmethod
    def after_email_proof(
        cls, *, token: str, user_id: Id, user_agent: str, at: datetime
    ) -> "Session":
        """A 24 hour session opened by a verified email code or link, never extended."""
        return cls(
            id=Id(),
            token_hash=hash_token(token),
            user_id=user_id,
            expires_at=at + EMAIL_PROOF_LIFETIME,
            lifetime=EMAIL_PROOF_LIFETIME,
            extendable=False,
            user_agent=user_agent[:300],
        )

    def is_expired(self, *, at: datetime) -> bool:
        return at >= self.expires_at

    def needs_extension(self, *, at: datetime) -> bool:
        return self.extendable and self.expires_at - at < self.lifetime / 2

    def extended(self, *, at: datetime) -> "Session":
        return dataclasses.replace(self, expires_at=at + self.lifetime)
