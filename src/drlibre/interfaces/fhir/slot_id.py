import base64
import binascii
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from drlibre.shared_kernel.ids import Id

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MINUTE = timedelta(minutes=1)
_SIZE = 36


@dataclass(frozen=True, slots=True)
class SlotKey:
    """What a `Slot` id names: the clinician profile, the appointment type and the start."""

    clinician_id: Id
    appointment_type_id: Id
    start: datetime


def slot_id(key: SlotKey) -> str:
    """Lower-case unpadded base32 of profile, type and start minute: 58 FHIR id characters."""
    minutes = (key.start - _EPOCH) // _MINUTE
    raw = key.clinician_id.value.bytes + key.appointment_type_id.value.bytes
    return _encoded(raw + minutes.to_bytes(4, "big"))


def slot_key(raw: str) -> SlotKey | None:
    """The key a slot id encodes, or None when it is not one."""
    padded = raw.upper() + "=" * (-len(raw) % 8)
    try:
        found = base64.b32decode(padded)
    except (binascii.Error, ValueError):
        return None
    if len(found) != _SIZE or _encoded(found) != raw:
        return None
    start = _EPOCH + int.from_bytes(found[32:], "big") * _MINUTE
    return SlotKey(Id(uuid.UUID(bytes=found[:16])), Id(uuid.UUID(bytes=found[16:32])), start)


def _encoded(raw: bytes) -> str:
    return base64.b32encode(raw).decode().rstrip("=").lower()
