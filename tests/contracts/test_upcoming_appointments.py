from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.application.ports.outbound import UpcomingAppointments
from drlibre.identity.infrastructure.upcoming_appointments import BookingUpcomingAppointments
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, stored_scene
from tests.fakes.upcoming_appointments import InMemoryUpcomingAppointments

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass
class Setup:
    appointments: UpcomingAppointments
    clinician_user: Id
    patient: Id
    book: Callable[[datetime, str], None]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    patient = Id()
    if request.param == "fake":
        fake = InMemoryUpcomingAppointments()
        clinician_user = Id()

        def add(start: datetime, status: str) -> None:
            active = status not in ("CANCELLED", "NO_SHOW")
            row = Dependent("appointment", Id(), "Rendez-vous")
            fake.rows.append((clinician_user, patient, start, active, row))

        return Setup(fake, clinician_user, patient, add)
    scene = stored_scene()
    profile = scene.clinicians[0]

    def store(start: datetime, status: str) -> None:
        DjangoAppointments().add(
            existing_appointment(
                patient_id=patient,
                clinician_id=profile.id,
                appointment_type_id=scene.kind,
                start=start,
                end=start.replace(minute=30),
                status=AppointmentStatus(status),
            )
        )

    return Setup(
        BookingUpcomingAppointments(DjangoBookingQueries()), profile.user_id, patient, store
    )


def test_a_user_without_appointments_blocks_neither_deactivation_nor_deletion(
    setup: Setup,
) -> None:
    user = Id()

    assert setup.appointments.active_upcoming_for_clinician(user, after=NOW) == ()
    assert setup.appointments.any_for_user(user) == ()


def test_only_active_appointments_after_the_instant_block_a_clinician_deactivation(
    setup: Setup,
) -> None:
    """Story utilisateurs : un praticien ayant des rendez-vous actifs à venir reste actif."""
    setup.book(datetime(2026, 11, 25, 9, tzinfo=UTC), "BOOKED")
    setup.book(datetime(2026, 11, 26, 9, tzinfo=UTC), "CANCELLED")
    setup.book(datetime(2026, 11, 19, 9, tzinfo=UTC), "BOOKED")

    found = setup.appointments.active_upcoming_for_clinician(setup.clinician_user, after=NOW)

    assert len(found) == 1


def test_any_appointment_of_a_patient_or_a_clinician_blocks_deleting_the_account(
    setup: Setup,
) -> None:
    """Story utilisateurs : un compte ayant des rendez-vous ne peut pas être supprimé."""
    setup.book(datetime(2026, 11, 19, 9, tzinfo=UTC), "CANCELLED")

    assert len(setup.appointments.any_for_user(setup.patient)) == 1
    assert len(setup.appointments.any_for_user(setup.clinician_user)) == 1
    assert setup.appointments.any_for_user(Id()) == ()
