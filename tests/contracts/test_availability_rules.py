import dataclasses
from dataclasses import dataclass
from datetime import date, time

import pytest

from drlibre.organisation.infrastructure.repositories import DjangoRooms
from drlibre.scheduling.application.ports.inbound import AvailabilityQueries, RoomUsage
from drlibre.scheduling.application.ports.outbound import AvailabilityRules
from drlibre.scheduling.infrastructure.queries import DjangoAvailabilityQueries
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_scheduling import rule, stored_department, stored_profile
from tests.fakes.scheduling import (
    InMemoryAvailabilityQueries,
    InMemoryAvailabilityRules,
    InMemoryTimeOffs,
)

REAL = [pytest.mark.integration, pytest.mark.django_db]


class Queries(AvailabilityQueries, RoomUsage):
    pass


@dataclass
class Setup:
    rules: AvailabilityRules
    queries: AvailabilityQueries
    usage: RoomUsage
    clinician: Id
    other: Id
    room: Id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    if request.param == "fake":
        rules = InMemoryAvailabilityRules()
        queries = InMemoryAvailabilityQueries(rules=rules, time_offs=InMemoryTimeOffs())
        return Setup(rules, queries, queries, Id(), Id(), Id())
    department = stored_department()
    room = build.room(department.id)
    DjangoRooms().save(room)
    real = DjangoAvailabilityQueries()
    clinician, other = stored_profile(department), stored_profile(department)
    return Setup(DjangoAvailabilityRules(), real, real, clinician.id, other.id, room.id)


def test_a_rule_is_stored_edited_and_deleted(setup: Setup) -> None:
    """Story plages : lister, créer, modifier et supprimer mes plages."""
    saved = rule(setup.clinician, weekday=1, valid_from=date(2026, 11, 20), room_id=setup.room)
    setup.rules.save(saved)
    moved = dataclasses.replace(saved, start=time(8), step_minutes=20, room_id=None)

    setup.rules.save(moved)

    assert setup.rules.get(saved.id) == moved
    assert setup.rules.for_clinician(setup.clinician) == (moved,)
    setup.rules.delete(saved.id)
    setup.rules.delete(Id())
    assert setup.rules.get(saved.id) is None


def test_a_clinician_lists_only_own_rules_by_weekday_then_start(setup: Setup) -> None:
    """Story plages : le praticien ne voit que ses propres plages."""
    tuesday = rule(setup.clinician, weekday=2, start=time(9), end=time(12))
    monday_late = rule(setup.clinician, weekday=1, start=time(14), end=time(18))
    monday = rule(setup.clinician, weekday=1, start=time(8), end=time(12))
    theirs = rule(setup.other, weekday=1)
    for each in (tuesday, monday_late, monday, theirs):
        setup.rules.save(each)

    assert setup.queries.rules_of(setup.clinician) == (monday, monday_late, tuesday)
    assert setup.queries.weekly_summary(frozenset({setup.clinician, Id()})) == {
        setup.clinician: (monday, monday_late, tuesday)
    }


def test_a_room_lists_the_rules_that_use_it(setup: Setup) -> None:
    """Story plages : une salle utilisée par une plage ne peut pas être supprimée."""
    used = rule(setup.clinician, weekday=1, start=time(9), end=time(12), room_id=setup.room)
    setup.rules.save(used)
    setup.rules.save(rule(setup.clinician, weekday=2))

    (dependent,) = setup.usage.rules_using(setup.room)

    assert (dependent.kind, dependent.id, dependent.label) == (
        "availability_rule",
        used.id,
        "Lundi 09:00-12:00",
    )
    assert setup.usage.rules_using(Id()) == ()


def test_the_daily_job_finds_each_clinician_with_rules_once(setup: Setup) -> None:
    """Story plages : cet horizon avance chaque jour sans intervention."""
    setup.rules.save(rule(setup.clinician, weekday=1))
    setup.rules.save(rule(setup.clinician, weekday=2))

    found = setup.rules.clinicians()

    assert found.count(setup.clinician) == 1
    assert setup.other not in found
