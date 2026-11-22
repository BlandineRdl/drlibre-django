from dataclasses import dataclass
from enum import StrEnum

from drlibre.shared_kernel.ids import Id


class ReaderKind(StrEnum):
    ANONYMOUS = "anonymous"
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class Reader:
    """Who reads, which bounds every interop row to what that user sees on screen."""

    kind: ReaderKind
    user_id: Id | None = None
    profile_id: Id | None = None

    @classmethod
    def anonymous(cls) -> "Reader":
        return cls(ReaderKind.ANONYMOUS)

    @property
    def is_admin(self) -> bool:
        return self.kind is ReaderKind.ADMIN

    @property
    def is_staff(self) -> bool:
        return self.kind is ReaderKind.CLINICIAN or self.kind is ReaderKind.ADMIN
