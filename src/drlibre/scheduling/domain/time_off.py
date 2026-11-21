from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors, invalid_field

MAX_REASON = 200


@dataclass(frozen=True, slots=True)
class TimeOff:
    """A period during which one clinician is unavailable."""

    id: Id
    clinician_id: Id
    start: datetime
    end: datetime
    reason: str

    @classmethod
    def from_form(
        cls, raw: Mapping[str, str], *, id: Id, clinician_id: Id, time_zone: ZoneInfo
    ) -> "TimeOff":
        """Start and end typed in the hospital's local time, stored in UTC."""
        f = FieldErrors()
        start = _local_instant(f, "start", raw.get("start", ""), time_zone)
        end = _local_instant(f, "end", raw.get("end", ""), time_zone)
        reason = f.text("reason", raw.get("reason", ""), required=False, max_length=MAX_REASON)
        f.raise_if_any()
        return cls(id, clinician_id, start, end, reason)

    def __post_init__(self) -> None:
        Period(self.start, self.end)
        if len(self.reason) > MAX_REASON:
            raise invalid_field("reason", f"{MAX_REASON} caractères au plus.")

    @property
    def period(self) -> Period:
        return Period(self.start, self.end)

    def same_period_as(self, other: "TimeOff") -> bool:
        return self.start == other.start and self.end == other.end


def _local_instant(f: FieldErrors, field: str, raw: str, time_zone: ZoneInfo) -> datetime:
    try:
        local = datetime.fromisoformat(raw.strip())
    except ValueError:
        local = None
    if local is None or local.tzinfo is not None:
        f.add(field, "Saisissez une date et une heure locales.")
        return datetime.min.replace(tzinfo=UTC)
    return local.replace(tzinfo=time_zone).astimezone(UTC)
