from drlibre.booking.application.ports.inbound import AppointmentQueries
from drlibre.scheduling.application.ports.outbound import BusyRoom, RoomBookings
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class BookingRoomBookings(RoomBookings):
    """Reads the rooms' active appointments through booking's inbound port."""

    def __init__(self, queries: AppointmentQueries) -> None:
        self._queries = queries

    def busy(self, room_ids: tuple[Id, ...], *, within: Period) -> tuple[BusyRoom, ...]:
        found = self._queries.room_periods(room_ids, start=within.start, end=within.end)
        return tuple(BusyRoom(r.appointment_id, r.room_id, Period(r.start, r.end)) for r in found)
