import dataclasses
from dataclasses import dataclass
from datetime import datetime

from drlibre.identity.domain.session import hash_token
from drlibre.shared_kernel.booking_policy import LINK_LIFETIME
from drlibre.shared_kernel.ids import Id

LINKS_PER_EMAIL_PER_HOUR = 3


@dataclass(frozen=True, slots=True)
class SignInLink:
    id: Id
    token_hash: str
    patient_id: Id
    expires_at: datetime
    used_at: datetime | None
    cancelled_at: datetime | None

    @classmethod
    def issue(cls, *, token: str, patient_id: Id, at: datetime) -> "SignInLink":
        return cls(Id(), hash_token(token), patient_id, at + LINK_LIFETIME, None, None)

    def usable(self, at: datetime) -> bool:
        return self.used_at is None and self.cancelled_at is None and at < self.expires_at

    def used(self, at: datetime) -> "SignInLink":
        return dataclasses.replace(self, used_at=at)

    def cancelled(self, at: datetime) -> "SignInLink":
        return dataclasses.replace(self, cancelled_at=at)
