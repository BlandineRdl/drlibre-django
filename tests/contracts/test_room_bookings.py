from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.scheduling.application.ports.outbound import BusyRoom, RoomBookings
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.infrastructure.booking_rooms import BookingRoomBookings
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, stored_scene
from tests.fakes.scheduling import InMemoryRoomBookings

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Setup:
    rooms: RoomBookings
    room: Id
    book: Callable[[datetime, datetime], Id]


def at(hour: int) -> datetime:
    return datetime(2026, 11, 23, hour, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    if request.param == "fake":
        fake, room = InMemoryRoomBookings(), Id()

        def add(start: datetime, end: datetime) -> Id:
            busy = BusyRoom(Id(), room, Period(start, end))
            fake.rows.append(busy)
            return busy.appointment_id

        return Setup(fake, room, add)
    scene = stored_scene()

    def store(start: datetime, end: datetime) -> Id:
        made = existing_appointment(
            patient_id=Id(),
            clinician_id=scene.clinicians[0].id,
            appointment_type_id=scene.kind,
            room_id=scene.room,
            start=start,
            end=end,
            status=AppointmentStatus.BOOKED,
        )
        DjangoAppointments().add(made)
        return made.id

    return Setup(BookingRoomBookings(DjangoBookingQueries()), scene.room, store)


def test_a_room_comes_back_busy_with_the_appointments_overlapping_the_range(setup: Setup) -> None:
    """Règle §6.2 : un créneau n'est montré que si une salle du département reste libre."""
    inside = setup.book(at(9), at(10))
    setup.book(at(11), at(12))

    found = setup.rooms.busy((setup.room,), within=Period(at(9), at(11)))

    assert found == (BusyRoom(inside, setup.room, Period(at(9), at(10))),)
    assert setup.rooms.busy((Id(),), within=Period(at(9), at(11))) == ()
