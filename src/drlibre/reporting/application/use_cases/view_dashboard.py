from zoneinfo import ZoneInfo

from drlibre.reporting.application.ports.inbound import ViewDashboard
from drlibre.reporting.application.ports.outbound import ActivityQueries, Admins
from drlibre.reporting.domain.available_minutes import available_minutes
from drlibre.reporting.domain.dashboard import BUSIEST_COUNT, Dashboard, Range
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class ViewDashboardUseCase(ViewDashboard):
    def __init__(
        self, *, clock: Clock, admins: Admins, queries: ActivityQueries, time_zone: str
    ) -> None:
        self._clock = clock
        self._admins = admins
        self._queries = queries
        self._zone = ZoneInfo(time_zone)

    def execute(self, *, actor_id: Id, period: Range) -> Dashboard:
        if not self._admins.is_admin(actor_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Réservé aux administrateurs.")
        now = self._clock.now()
        available = 0
        for schedule in self._queries.schedules(*period.window(now)):
            zone = ZoneInfo(schedule.time_zone)
            days = period.days(now.astimezone(zone).date())
            available += available_minutes(schedule.rules, schedule.absences, days, zone)
        activity = self._queries.activity(now, period, BUSIEST_COUNT)
        return Dashboard.from_figures(
            period=period,
            tally=activity.tally,
            available_minutes=available,
            waitlist_size=self._queries.waitlist_size(),
            days=period.days(now.astimezone(self._zone).date()),
            counted=activity.per_day,
            busiest=activity.busiest,
        )
