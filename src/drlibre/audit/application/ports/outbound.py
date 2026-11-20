from typing import Protocol

from drlibre.audit.domain.audit_entry import AuditEntry, UnsafeMetadataError

__all__ = ["AuditEntry", "AuditLog", "UnsafeMetadataError"]


class AuditLog(Protocol):
    def record(self, entry: AuditEntry) -> None:
        """Append the entry inside the current unit of work; raise if it cannot be stored."""
        ...
