from dataclasses import dataclass
from datetime import datetime, timedelta

from drlibre.identity.domain.session import hash_token
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors

MAX_DAYS = 365


@dataclass(frozen=True, slots=True)
class ApiToken:
    """A bearer token carrying one user's rights until it expires; only its hash is kept."""

    id: Id
    token_hash: str
    user_id: Id
    label: str
    expires_at: datetime

    @classmethod
    def issue(cls, *, token: str, user_id: Id, label: str, days: int, at: datetime) -> "ApiToken":
        errors = FieldErrors()
        name = errors.text("label", label, max_length=100)
        if not 1 <= days <= MAX_DAYS:
            errors.add("days", f"De 1 à {MAX_DAYS} jours.")
        errors.raise_if_any()
        return cls(Id(), hash_token(token), user_id, name, at + timedelta(days=days))

    def is_expired(self, *, at: datetime) -> bool:
        return at >= self.expires_at
