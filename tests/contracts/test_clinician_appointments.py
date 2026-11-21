from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.scheduling.application.ports.outbound import ClinicianAppointments
from drlibre.scheduling.domain.appointment import AppointmentStatus as SlotStatus
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.infrastructure.booking_appointments import BookingClinicianAppointments
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import stored_scene
from tests.builders_scheduling import appointment
from tests.fakes.scheduling import InMemoryClinicianAppointments

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Setup:
    appointments: ClinicianAppointments
    clinician: Id
    other: Id
    book: Callable[[Id, datetime, datetime, str], None]


def at(day: int, hour: int) -> datetime:
    return datetime(2026, 11, day, hour, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    if request.param == "fake":
        fake = InMemoryClinicianAppointments()
        first, second = Id(), Id()

        def add(clinician: Id, start: datetime, end: datetime, status: str) -> None:
            fake.rows.append(appointment(clinician, start, end, status=status))

        return Setup(fake, first, second, add)
    scene = stored_scene()
    first, second = scene.clinicians[0].id, scene.clinicians[1].id

    def store(clinician: Id, start: datetime, end: datetime, status: str) -> None:
        DjangoAppointments().add(
            Appointment(
                id=Id(),
                patient_id=Id(),
                clinician_id=clinician,
                appointment_type_id=scene.kind,
                room_id=None,
                start=start,
                end=end,
                status=AppointmentStatus(status),
                source=Source.ONLINE,
            )
        )

    return Setup(BookingClinicianAppointments(DjangoBookingQueries()), first, second, store)


def test_a_clinician_without_appointments_has_none_in_any_range(setup: Setup) -> None:
    within = Period(at(23, 0), at(24, 0))

    assert setup.appointments.for_clinician(setup.clinician, within=within) == ()


def test_appointments_overlapping_the_range_come_back_whatever_their_status(setup: Setup) -> None:
    """Décision du plan : les créneaux lisent les rendez-vous de booking, le statut inclus."""
    setup.book(setup.clinician, at(23, 9), at(23, 10), "BOOKED")
    setup.book(setup.clinician, at(23, 11), at(23, 12), "CANCELLED")
    setup.book(setup.clinician, at(23, 8), at(23, 9), "BOOKED")
    setup.book(setup.other, at(23, 9), at(23, 10), "BOOKED")

    found = setup.appointments.for_clinician(setup.clinician, within=Period(at(23, 9), at(23, 12)))

    assert sorted((a.period.start, a.status) for a in found) == [
        (at(23, 9), SlotStatus.BOOKED),
        (at(23, 11), SlotStatus.CANCELLED),
    ]
    assert [a.active for a in sorted(found, key=lambda a: a.period.start)] == [True, False]
