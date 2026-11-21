from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from drlibre.shared_kernel.ids import Id

BUSIEST_COUNT = 5


class Range(StrEnum):
    """Spec 10: today, 7 days or 30 days ending today."""

    TODAY = "today"
    WEEK = "7"
    MONTH = "30"

    @classmethod
    def parse(cls, raw: str | None) -> "Range":
        """An unusable value falls back to 7 days."""
        try:
            return cls(raw or "")
        except ValueError:
            return cls.WEEK

    @property
    def length(self) -> int:
        return 1 if self is Range.TODAY else int(self.value)

    def days(self, today: date) -> tuple[date, ...]:
        """The range's local days, oldest first, ending today."""
        return tuple(today - timedelta(days=back) for back in reversed(range(self.length)))

    def window(self, now: datetime) -> tuple[datetime, datetime]:
        """UTC instants covering the range's days in every time zone."""
        utc = now.astimezone(UTC)
        return utc - timedelta(days=self.length + 1), utc + timedelta(days=1)


@dataclass(frozen=True, slots=True)
class Ratio:
    num: int
    den: int

    @property
    def percent(self) -> int | None:
        """Rounded half up; None for a zero denominator, shown as « n/a »."""
        if self.den == 0:
            return None
        return (200 * self.num + self.den) // (2 * self.den)


@dataclass(frozen=True, slots=True)
class Tally:
    """Appointments starting in the range."""

    appointments: int
    cancellations: int
    no_shows: int
    online: int
    active_minutes: int


@dataclass(frozen=True, slots=True)
class DayCount:
    day: date
    count: int


@dataclass(frozen=True, slots=True)
class BusyClinician:
    clinician_id: Id
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class Dashboard:
    range: Range
    appointments: int
    cancellations: int
    utilisation: Ratio
    no_show_rate: Ratio
    online_share: Ratio
    waitlist_size: int
    per_day: tuple[DayCount, ...]
    busiest: tuple[BusyClinician, ...]

    @classmethod
    def from_figures(
        cls,
        *,
        period: Range,
        tally: Tally,
        available_minutes: int,
        waitlist_size: int,
        days: tuple[date, ...],
        counted: tuple[DayCount, ...],
        busiest: tuple[BusyClinician, ...],
    ) -> "Dashboard":
        counts = {c.day: c.count for c in counted}
        return cls(
            range=period,
            appointments=tally.appointments,
            cancellations=tally.cancellations,
            utilisation=Ratio(tally.active_minutes, available_minutes),
            no_show_rate=Ratio(tally.no_shows, tally.appointments),
            online_share=Ratio(tally.online, tally.appointments),
            waitlist_size=waitlist_size,
            per_day=tuple(DayCount(d, counts.get(d, 0)) for d in sorted({*days, *counts})),
            busiest=busiest[:BUSIEST_COUNT],
        )
