import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from drlibre.shared_kernel.ids import Id

type MetadataValue = str | int | bool | tuple[str, ...]

# Codes, status values, field names and email domains; rules out emails and free text.
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,99}")


class UnsafeMetadataError(ValueError):
    pass


def _clean(key: str, value: object) -> MetadataValue:
    if isinstance(value, Id):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, bool | int):
        return value
    if isinstance(value, str) and _TOKEN.fullmatch(value):
        return value
    if isinstance(value, tuple) and all(isinstance(v, str | Id) for v in value):
        items = tuple(str(v) for v in value)
        if all(_TOKEN.fullmatch(v) for v in items):
            return items
    raise UnsafeMetadataError(f"audit metadata {key!r} must be an id, a count, a status or names")


@dataclass(frozen=True, slots=True)
class AuditEntry:
    actor: Id | None
    action: str
    entity_type: str
    entity_id: Id | None
    metadata: tuple[tuple[str, MetadataValue], ...]
    at: datetime

    @classmethod
    def from_event(
        cls,
        *,
        actor: Id | None,
        action: str,
        entity_type: str,
        entity_id: Id | None,
        at: datetime,
        metadata: Mapping[str, object] | None = None,
    ) -> "AuditEntry":
        cleaned = tuple((key, _clean(key, value)) for key, value in (metadata or {}).items())
        return cls(actor, action, entity_type, entity_id, cleaned, at)
