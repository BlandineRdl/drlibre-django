from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.shared_kernel.booking_policy import SLOT_HORIZON_DAYS

ONE_WEEK = timedelta(days=7)


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass(frozen=True, slots=True)
class Week:
    """A Monday-to-Sunday week of the hospital's zone, kept within the slot horizon."""

    monday: date
    previous: date | None
    following: date | None
    start: datetime
    end: datetime

    @classmethod
    def within_horizon(cls, *, asked: date | None, now: datetime, time_zone: str) -> "Week":
        """The asked week, or the current one when none is asked or it lies outside the horizon."""
        zone = ZoneInfo(time_zone)
        today = now.astimezone(zone).date()
        first, last = _monday(today), _monday(today + timedelta(days=SLOT_HORIZON_DAYS))
        monday = _monday(asked) if asked else first
        if not first <= monday <= last:
            monday = first
        return cls(
            monday=monday,
            previous=monday - ONE_WEEK if monday > first else None,
            following=monday + ONE_WEEK if monday < last else None,
            start=datetime.combine(monday, time(), zone),
            end=datetime.combine(monday + ONE_WEEK, time(), zone),
        )
