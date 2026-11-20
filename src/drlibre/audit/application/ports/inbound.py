from typing import Protocol

from drlibre.shared_kernel.ids import Id


class AuditQueries(Protocol):
    def has_acted(self, actor: Id) -> bool:
        """True when the user is the actor of at least one audit entry."""
        ...
