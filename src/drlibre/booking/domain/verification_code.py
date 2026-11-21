import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from drlibre.shared_kernel.ids import Id

CODE_LIFETIME = timedelta(minutes=10)
MAX_ATTEMPTS = 5


class CodePurpose(StrEnum):
    BOOKING = "BOOKING"


@dataclass(frozen=True, slots=True)
class VerificationCode:
    """The hash of a code sent to an email for one hold; 10 minutes and 5 attempts."""

    hold_id: Id
    email: str
    purpose: CodePurpose
    code_hash: str
    expires_at: datetime
    attempts: int = 0

    @classmethod
    def issue(cls, *, hold_id: Id, email: str, code_hash: str, at: datetime) -> "VerificationCode":
        return cls(hold_id, email, CodePurpose.BOOKING, code_hash, at + CODE_LIFETIME)

    def is_usable(self, at: datetime) -> bool:
        return at < self.expires_at and self.attempts < MAX_ATTEMPTS

    def failed_once(self) -> "VerificationCode":
        return dataclasses.replace(self, attempts=self.attempts + 1)
