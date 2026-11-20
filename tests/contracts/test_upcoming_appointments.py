from datetime import UTC, datetime

import pytest

from drlibre.identity.application.ports.outbound import UpcomingAppointments
from drlibre.identity.infrastructure.upcoming_appointments import NoAppointmentsYet
from drlibre.shared_kernel.ids import Id
from tests.fakes.upcoming_appointments import InMemoryUpcomingAppointments


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="null-until-scheduling")]
)
def appointments(request: pytest.FixtureRequest) -> UpcomingAppointments:
    return InMemoryUpcomingAppointments() if request.param == "fake" else NoAppointmentsYet()


def test_a_user_without_appointments_blocks_neither_deactivation_nor_deletion(
    appointments: UpcomingAppointments,
) -> None:
    user = Id()

    assert (
        appointments.active_upcoming_for_clinician(user, after=datetime(2026, 11, 20, tzinfo=UTC))
        == ()
    )
    assert appointments.any_for_user(user) == ()
