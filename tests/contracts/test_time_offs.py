from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from drlibre.scheduling.application.ports.inbound import AvailabilityQueries
from drlibre.scheduling.application.ports.outbound import TimeOffs
from drlibre.scheduling.infrastructure.queries import DjangoAvailabilityQueries
from drlibre.scheduling.infrastructure.repositories import DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import stored_department, stored_profile, time_off
from tests.fakes.scheduling import (
    InMemoryAvailabilityQueries,
    InMemoryAvailabilityRules,
    InMemoryTimeOffs,
)

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Setup:
    time_offs: TimeOffs
    queries: AvailabilityQueries
    clinician: Id
    other: Id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    if request.param == "fake":
        time_offs = InMemoryTimeOffs()
        queries = InMemoryAvailabilityQueries(
            rules=InMemoryAvailabilityRules(), time_offs=time_offs
        )
        return Setup(time_offs, queries, Id(), Id())
    department = stored_department()
    clinician, other = stored_profile(department), stored_profile(department)
    return Setup(DjangoTimeOffs(), DjangoAvailabilityQueries(), clinician.id, other.id)


def at(day: int, hour: int) -> datetime:
    return datetime(2026, 12, day, hour, tzinfo=UTC)


def test_a_time_off_is_stored_and_deleted(setup: Setup) -> None:
    """Story absences : lister, créer et supprimer mes absences."""
    saved = time_off(setup.clinician, at(1, 8), at(1, 11))
    setup.time_offs.save(saved)

    assert setup.time_offs.get(saved.id) == saved
    assert setup.time_offs.for_clinician(setup.clinician) == (saved,)
    setup.time_offs.delete(saved.id)
    setup.time_offs.delete(Id())
    assert setup.time_offs.get(saved.id) is None


def test_a_clinician_lists_only_own_time_off_by_start(setup: Setup) -> None:
    """Story absences : le praticien ne voit que ses propres absences."""
    later = time_off(setup.clinician, at(3, 8), at(3, 9))
    sooner = time_off(setup.clinician, at(1, 8), at(1, 9))
    for each in (later, sooner, time_off(setup.other, at(2, 8), at(2, 9))):
        setup.time_offs.save(each)

    assert setup.queries.time_offs_of(setup.clinician) == (sooner, later)
