from typing import Protocol

from drlibre.interop.domain.reader import Reader, ReaderKind
from drlibre.shared_kernel.ids import Id

__all__ = ["Reader", "ReaderKind", "Readers"]


class Readers(Protocol):
    def of(self, user_id: Id | None) -> Reader:
        """None is anonymous; a profile is a clinician, an active admin an admin, else patient."""
        ...
