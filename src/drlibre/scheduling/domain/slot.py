from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field


@dataclass(frozen=True, slots=True)
class Period:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise invalid_field("start", "Les instants doivent porter un fuseau horaire.")
        if self.end <= self.start:
            raise invalid_field("end", "La fin doit suivre le début.")

    def overlaps(self, other: "Period") -> bool:
        return self.start < other.end and other.start < self.end

    def covers(self, other: "Period") -> bool:
        return self.start <= other.start and other.end <= self.end

    def extended(self, by: timedelta) -> "Period":
        return Period(self.start, self.end + by)


@dataclass(frozen=True, slots=True)
class Slot:
    """A free start time lasting the appointment type's duration, in UTC."""

    start: datetime
    end: datetime

    @property
    def period(self) -> Period:
        return Period(self.start, self.end)


class SlotStatus(StrEnum):
    """Spec §15.2: free, or taken by an active appointment, an open hold or time off."""

    FREE = "free"
    BUSY = "busy"
    TENTATIVE = "busy-tentative"
    UNAVAILABLE = "busy-unavailable"


@dataclass(frozen=True, slots=True)
class SlotState:
    """One start of a clinician's rule, in UTC, with what holds it."""

    clinician_id: Id
    rule_id: Id
    start: datetime
    end: datetime
    status: SlotStatus
