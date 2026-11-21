from typing import Protocol

from drlibre.audit.domain.audit_entry import AuditEntry, UnsafeMetadataError
from drlibre.shared_kernel.ids import Id

__all__ = ["AuditEntry", "AuditLog", "JournalActors", "UnsafeMetadataError"]


class AuditLog(Protocol):
    def record(self, entry: AuditEntry) -> None:
        """Append the entry inside the current unit of work; raise if it cannot be stored."""
        ...


class JournalActors(Protocol):
    def is_admin(self, user_id: Id) -> bool:
        """Whether the id is an active admin."""
        ...

    def id_of(self, email: str) -> Id | None:
        """The user of the email, trimmed and any case, active or not, or None."""
        ...

    def emails_of(self, user_ids: frozenset[Id]) -> dict[Id, str]:
        """The email of each known user; unknown ids are left out."""
        ...
