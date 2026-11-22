from bisect import bisect_left
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
        blocked = sorted(
            [t.period for t in self.time_off] + [b.extended(self.buffer) for b in self.busy],
            key=lambda b: b.start,
        )
        starts = [b.start for b in blocked]
        longest = max((b.end - b.start for b in blocked), default=timedelta())

        def is_blocked(slot: Slot) -> bool:
            # Only periods starting within `longest` before the slot can overlap it.
            near = blocked[
                bisect_left(starts, slot.start - longest) : bisect_left(starts, slot.end)
            ]
            return any(b.end > slot.start for b in near)

        found = {
            slot
            for slot in self._proposed(window)
            if window.covers(slot.period) and not is_blocked(slot)
        }
        return tuple(sorted(found, key=lambda s: s.start))

    def rule_of(self, slot: Slot) -> AvailabilityRule | None:
        """The rule proposing the slot, the earliest starting one when several do."""
        day = slot.start.astimezone(self.time_zone).date()
        ordered = sorted(self.rules, key=lambda r: (r.start, str(r.id)))
        return next(
            (r for r in ordered if r.applies_on(day) and slot in self._rule_slots(r, day)), None
        )

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
