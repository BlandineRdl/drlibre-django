from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

LEAD_TIME = timedelta(minutes=120)
HORIZON = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class Horizon:
    """The span next availabilities are looked for: now plus lead time to 90 days ahead."""

    now: datetime
    start: datetime
    end: datetime

    @classmethod
    def at(cls, now: datetime) -> "Horizon":
        return cls(now=now, start=now + LEAD_TIME, end=now + HORIZON)

    def local_days(self, time_zone: str) -> tuple[date, date]:
        zone = ZoneInfo(time_zone)
        return self.start.astimezone(zone).date(), self.end.astimezone(zone).date()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())
