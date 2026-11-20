from dataclasses import dataclass
from datetime import datetime

from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

MAX_REASON = 200


@dataclass(frozen=True, slots=True)
class TimeOff:
    """A period during which one clinician is unavailable."""

    id: Id
    clinician_id: Id
    start: datetime
    end: datetime
    reason: str

    def __post_init__(self) -> None:
        Period(self.start, self.end)
        if len(self.reason) > MAX_REASON:
            raise invalid_field("reason", f"{MAX_REASON} caractères au plus.")

    @property
    def period(self) -> Period:
        return Period(self.start, self.end)
