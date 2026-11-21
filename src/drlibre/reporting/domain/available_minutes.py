from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

type Interval = tuple[datetime, datetime]


@dataclass(frozen=True, slots=True)
class RuleHours:
    """A weekly availability rule; weekday 0 is Sunday, as in scheduling."""

    weekday: int
    start: time
    end: time
    valid_from: date
    valid_to: date | None

    def applies_on(self, day: date) -> bool:
        return (
            day.isoweekday() % 7 == self.weekday
            and self.valid_from <= day
            and (self.valid_to is None or day <= self.valid_to)
        )


@dataclass(frozen=True, slots=True)
class Absence:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class ClinicianSchedule:
    """An active clinician's rules and time off, in their hospital's zone."""

    time_zone: str
    rules: tuple[RuleHours, ...]
    absences: tuple[Absence, ...]


def available_minutes(
    rules: Sequence[RuleHours], absences: Sequence[Absence], days: Iterable[date], zone: ZoneInfo
) -> int:
    """Spec 13: rule hours on the days, minus the union of time off, in whole minutes."""
    hours = _union(
        (_instant(day, rule.start, zone), _instant(day, rule.end, zone))
        for day in days
        for rule in rules
        if rule.applies_on(day)
    )
    off = _union((a.start, a.end) for a in absences)
    seconds = sum((end - start).total_seconds() for start, end in hours)
    seconds -= sum(_overlap(h, o) for h in hours for o in off)
    return int(seconds // 60)


def _instant(day: date, at: time, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, at, tzinfo=zone).astimezone(UTC)


def _union(intervals: Iterable[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(i for i in intervals if i[0] < i[1]):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _overlap(a: Interval, b: Interval) -> float:
    return max(0.0, (min(a[1], b[1]) - max(a[0], b[0])).total_seconds())
