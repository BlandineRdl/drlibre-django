from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    ClinicianFilter,
    ClinicianWeek,
    ClinicianWeekView,
)
from drlibre.booking.application.ports.outbound import BookingDirectory, ClinicianAgenda
from drlibre.booking.application.use_cases.clinician_read_helpers import (
    ONE_DAY,
    time_zone_of,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class ClinicianWeekUseCase(ClinicianWeek):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, week: date | None) -> ClinicianWeekView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = time_zone_of(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        asked = week or self._clock.now().astimezone(zone).date()
        monday = asked - timedelta(days=asked.weekday())
        start = datetime.combine(monday, time(), zone)
        end = datetime.combine(monday + 7 * ONE_DAY, time(), zone)
        found = self._agenda.entries(profile_id, ClinicianFilter(start=start, end=end))
        active = tuple(e for e in found if e.appointment.active)
        return ClinicianWeekView(monday, time_zone, active)
