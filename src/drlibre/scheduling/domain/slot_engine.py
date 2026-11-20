from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.domain.time_off import TimeOff


@dataclass(frozen=True, slots=True)
class SlotEngine:
    """Spec 5.1 steps 1 to 4 for one clinician and one appointment type; never reads the clock."""

    rules: Sequence[AvailabilityRule]
    time_off: Sequence[TimeOff]
    busy: Sequence[Period]
    duration: timedelta
    buffer: timedelta
    time_zone: ZoneInfo

    def free_slots(self, window: Period) -> tuple[Slot, ...]:
        blocked = [t.period for t in self.time_off] + [b.extended(self.buffer) for b in self.busy]
        found = {
            slot
            for slot in self._proposed(window)
            if window.covers(slot.period) and not any(slot.period.overlaps(b) for b in blocked)
        }
        return tuple(sorted(found, key=lambda s: s.start))

    def _proposed(self, window: Period) -> Iterator[Slot]:
        for day in _local_days(window, self.time_zone):
            for rule in self.rules:
                if rule.applies_on(day):
                    yield from self._rule_slots(rule, day)

    def _rule_slots(self, rule: AvailabilityRule, day: date) -> Iterator[Slot]:
        # Wall-clock bounds become UTC instants; stepping in UTC keeps real durations across DST.
        start = self._instant(day, rule.start)
        stop = self._instant(day, rule.end)
        step = timedelta(minutes=rule.step_minutes)
        while start + self.duration <= stop:
            yield Slot(start, start + self.duration)
            start += step

    def _instant(self, day: date, at: time) -> datetime:
        return datetime.combine(day, at, tzinfo=self.time_zone).astimezone(UTC)


def _local_days(window: Period, tz: ZoneInfo) -> Iterator[date]:
    day = window.start.astimezone(tz).date()
    last = window.end.astimezone(tz).date()
    while day <= last:
        yield day
        day += timedelta(days=1)
