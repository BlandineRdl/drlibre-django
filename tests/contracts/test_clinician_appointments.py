from datetime import UTC, datetime

import pytest

from drlibre.scheduling.application.ports.outbound import ClinicianAppointments
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.infrastructure.no_appointments_yet import NoAppointmentsYet
from drlibre.shared_kernel.ids import Id
from tests.fakes.scheduling import InMemoryClinicianAppointments


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="null-until-booking")]
)
def appointments(request: pytest.FixtureRequest) -> ClinicianAppointments:
    return InMemoryClinicianAppointments() if request.param == "fake" else NoAppointmentsYet()


def test_a_clinician_without_appointments_has_none_in_any_range(
    appointments: ClinicianAppointments,
) -> None:
    within = Period(datetime(2026, 11, 23, tzinfo=UTC), datetime(2026, 11, 24, tzinfo=UTC))

    assert appointments.for_clinician(Id(), within=within) == ()
