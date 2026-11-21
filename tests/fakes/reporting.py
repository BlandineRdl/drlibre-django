from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from drlibre.identity.domain.user import Role
from drlibre.reporting.application.ports.outbound import ActivityQueries, Admins
from drlibre.reporting.domain.available_minutes import Absence, ClinicianSchedule, RuleHours
from drlibre.reporting.domain.dashboard import BusyClinician, DayCount, Range, Tally
from drlibre.shared_kernel.ids import Id
from tests.fakes.users import InMemoryUsers


@dataclass(frozen=True, slots=True)
class ActivityAppointment:
    clinician_id: Id
    clinician_name: str
    time_zone: str
    start: datetime
    end: datetime
    status: str
    source: str


@dataclass
class ActivityClinician:
    time_zone: str
    active: bool = True
    rules: list[RuleHours] = field(default_factory=list)
    absences: list[Absence] = field(default_factory=list)


class InMemoryActivityQueries(ActivityQueries):
    """Rows the test adds; each filter mirrors the SQL statement it stands for."""

    def __init__(self) -> None:
        self.appointments: list[ActivityAppointment] = []
        self.waitlist: list[str] = []
        self.clinicians: dict[Id, ActivityClinician] = {}

    def _in_range(self, now: datetime, period: Range) -> list[ActivityAppointment]:
        def inside(a: ActivityAppointment) -> bool:
            zone = ZoneInfo(a.time_zone)
            return a.start.astimezone(zone).date() in period.days(now.astimezone(zone).date())

        return [a for a in self.appointments if inside(a)]

    def tally(self, now: datetime, period: Range) -> Tally:
        rows = self._in_range(now, period)
        kept = [a for a in rows if a.status != "CANCELLED"]
        working = {i for i, c in self.clinicians.items() if c.active}
        active = [a for a in kept if a.status != "NO_SHOW" and a.clinician_id in working]
        return Tally(
            appointments=len(kept),
            cancellations=len(rows) - len(kept),
            no_shows=sum(a.status == "NO_SHOW" for a in kept),
            online=sum(a.source in ("ONLINE", "ROUND_ROBIN") for a in kept),
            active_minutes=int(sum((a.end - a.start).total_seconds() for a in active) // 60),
        )

    def per_day(self, now: datetime, period: Range) -> tuple[DayCount, ...]:
        counts: dict[date, int] = {}
        for a in self._in_range(now, period):
            if a.status != "CANCELLED":
                day = a.start.astimezone(ZoneInfo(a.time_zone)).date()
                counts[day] = counts.get(day, 0) + 1
        return tuple(DayCount(day, counts[day]) for day in sorted(counts))

    def busiest(self, now: datetime, period: Range, limit: int) -> tuple[BusyClinician, ...]:
        counts: dict[tuple[Id, str], int] = {}
        for a in self._in_range(now, period):
            if a.status != "CANCELLED":
                key = (a.clinician_id, a.clinician_name)
                counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][1], str(kv[0][0])))
        return tuple(BusyClinician(key[0], key[1], count) for key, count in ranked[:limit])

    def waitlist_size(self) -> int:
        return sum(status in ("WAITING", "OFFERED") for status in self.waitlist)

    def schedules(self, start: datetime, end: datetime) -> tuple[ClinicianSchedule, ...]:
        return tuple(
            ClinicianSchedule(
                time_zone=c.time_zone,
                rules=tuple(c.rules),
                absences=tuple(a for a in c.absences if a.start < end and a.end > start),
            )
            for c in self.clinicians.values()
            if c.active
        )


class InMemoryAdmins(Admins):
    """Admins are the active ADMIN users of the in-memory users."""

    def __init__(self, users: InMemoryUsers) -> None:
        self.users = users

    def is_admin(self, user_id: Id) -> bool:
        user = self.users.rows.get(user_id)
        return user is not None and user.active and user.role is Role.ADMIN
