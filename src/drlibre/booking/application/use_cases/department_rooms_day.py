from datetime import date
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import DepartmentRoomsDay, RoomsDayView
from drlibre.booking.application.ports.outbound import BookingDirectory, ClinicianAgenda
from drlibre.booking.application.use_cases.clinician_read_helpers import (
    day_bounds,
    time_zone_of,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class DepartmentRoomsDayUseCase(DepartmentRoomsDay):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, day: date | None) -> RoomsDayView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = time_zone_of(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        shown = day or self._clock.now().astimezone(zone).date()
        start, end = day_bounds(shown, zone)
        found = self._agenda.room_day(profile_id, start, end)
        return RoomsDayView(shown, time_zone, found.rooms, found.bookings)
