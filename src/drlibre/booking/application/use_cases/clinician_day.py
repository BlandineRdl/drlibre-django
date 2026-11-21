from datetime import date
from itertools import groupby
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    AgendaHour,
    ClinicianDay,
    ClinicianDayView,
    ClinicianEntry,
    ClinicianFilter,
    DayCounts,
)
from drlibre.booking.application.ports.outbound import BookingDirectory, ClinicianAgenda
from drlibre.booking.application.use_cases.clinician_read_helpers import (
    day_bounds,
    time_zone_of,
    with_actions,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


def _count(entries: tuple[ClinicianEntry, ...], status: AppointmentStatus) -> int:
    return sum(1 for e in entries if e.appointment.status is status)


class ClinicianDayUseCase(ClinicianDay):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, day: date | None) -> ClinicianDayView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = time_zone_of(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        now = self._clock.now()
        shown = day or now.astimezone(zone).date()
        start, end = day_bounds(shown, zone)
        found = self._agenda.entries(profile_id, ClinicianFilter(start=start, end=end))
        entries = tuple(with_actions(e) for e in found)
        hours = tuple(
            AgendaHour(hour, tuple(group))
            for hour, group in groupby(
                entries, key=lambda e: e.appointment.start.astimezone(zone).hour
            )
        )
        counts = DayCounts(
            appointments=len(entries) - _count(entries, AppointmentStatus.CANCELLED),
            cancelled=_count(entries, AppointmentStatus.CANCELLED),
            completed=_count(entries, AppointmentStatus.COMPLETED),
            no_show=_count(entries, AppointmentStatus.NO_SHOW),
        )
        next_free = self._agenda.next_free_slot(profile_id, max(now, start), now)
        return ClinicianDayView(shown, time_zone, hours, counts, next_free)
