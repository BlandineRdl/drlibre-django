from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class AuditRecordView:
    """Who did what and when to one entity; metadata stays in the audit context."""

    actor_id: Id | None
    action: str
    at: datetime


class AuditQueries(Protocol):
    def has_acted(self, actor: Id) -> bool:
        """True when the user is the actor of at least one audit entry."""
        ...

    def entries_for(self, entity_type: str, entity_id: Id) -> tuple[AuditRecordView, ...]:
        """The entity's audit entries, oldest first; empty when there is none."""
        ...
