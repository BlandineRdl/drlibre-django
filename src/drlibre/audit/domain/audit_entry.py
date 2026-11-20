import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from drlibre.shared_kernel.ids import Id

type MetadataValue = str | int | bool | tuple[str, ...]

# Free text is allowed only under these keys; elsewhere a plain string could be a name.
_TEXT_KEYS = {"email_domain": re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")}
_FIELD_NAME = re.compile(r"[a-z_][a-z0-9_]{0,63}")


class UnsafeMetadataError(ValueError):
    pass


def _clean(key: str, value: object) -> MetadataValue:
    """Keep ids, counts, enum statuses, field-name tuples and allow-listed text only."""
    if isinstance(value, Id):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, bool | int):
        return value
    pattern = _TEXT_KEYS.get(key)
    if isinstance(value, str) and pattern is not None and pattern.fullmatch(value):
        return value
    if isinstance(value, tuple) and all(
        isinstance(v, Id) or (isinstance(v, str) and _FIELD_NAME.fullmatch(v)) for v in value
    ):
        return tuple(str(v) for v in value)
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
