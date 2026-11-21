from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import pytest

from drlibre.organisation.infrastructure.repositories import DjangoAppointmentTypes
from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    Clinician,
    SlotQueries,
    SlotStore,
)
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.infrastructure.slot_queries import DjangoSlotQueries
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_scheduling import rule, stored_department, stored_profile
from tests.fakes.clock import FixedClock
from tests.fakes.scheduling import (
    FixedSchedulingDirectory,
    InMemoryAvailabilityRules,
    InMemoryClinicianAppointments,
    InMemorySlotStore,
    InMemoryTimeOffs,
)

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
PARIS = ZoneInfo("Europe/Paris")


@dataclass
class Setup:
    store: SlotStore
    queries: SlotQueries
    department: Id
    clinicians: tuple[Id, Id]
    types: tuple[Id, Id]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def setup(request: pytest.FixtureRequest) -> Setup:
    if request.param == "fake":
        fake = InMemorySlotStore()
        return Setup(fake, fake, Id(), (Id(), Id()), (Id(), Id()))
    department = stored_department()
    kinds = build.appointment_type(department.id), build.appointment_type(department.id)
    for kind in kinds:
        DjangoAppointmentTypes().save(kind)
    a, b = stored_profile(department), stored_profile(department)
    return Setup(
        DjangoSlotStore(),
        DjangoSlotQueries(),
        department.id,
        (a.id, b.id),
        (kinds[0].id, kinds[1].id),
    )


class Refresh:
    """Runs the real RefreshSlots over the store under test, with in-memory rules."""

    def __init__(self, setup: Setup) -> None:
        self.clock = FixedClock(NOW)
        self.directory = FixedSchedulingDirectory()
        self.rules = InMemoryAvailabilityRules()
        self.store = setup.store
        for clinician in setup.clinicians:
            self.directory.clinicians[clinician] = Clinician(
                clinician, setup.department, "Europe/Paris", active=True
            )
        for kind, minutes in zip(setup.types, (30, 60), strict=True):
            self.directory.types[kind] = AppointmentType(
                kind, setup.department, minutes, 0, active=True, time_zone="Europe/Paris"
            )

    def __call__(self, clinician: Id) -> None:
        RefreshSlotsUseCase(
            clock=self.clock,
            directory=self.directory,
            rules=self.rules,
            time_offs=InMemoryTimeOffs(),
            appointments=InMemoryClinicianAppointments(),
            store=self.store,
        ).execute(clinician_id=clinician)


def paris(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=PARIS)


def starts(
    setup: Setup, kind: Id, clinicians: tuple[Id, ...], *, not_before: datetime = NOW
) -> list[datetime]:
    found = setup.queries.free_slots(
        kind, clinicians, within=Period(paris(23, 0), paris(24, 0)), not_before=not_before
    )
    return [found_slot.slot.start for found_slot in found]


def test_the_same_refresh_gives_the_same_slots_for_each_type(setup: Setup) -> None:
    """Story plages : chaque créneau dure la durée du type."""
    refresh = Refresh(setup)
    a = setup.clinicians[0]
    refresh.rules.save(rule(a, weekday=1, start=time(9), end=time(10), step_minutes=30))
    refresh(a)

    thirty = setup.queries.free_slots(
        setup.types[0], (a,), within=Period(paris(23, 0), paris(24, 0)), not_before=NOW
    )
    assert [(s.slot.start, s.slot.end) for s in thirty] == [
        (paris(23, 9), paris(23, 9, 30)),
        (paris(23, 9, 30), paris(23, 10)),
    ]
    assert starts(setup, setup.types[1], (a,)) == [paris(23, 9)]


def test_a_refresh_replaces_only_that_clinicians_slots(setup: Setup) -> None:
    """Story plages : une plage créée, modifiée ou supprimée change les créneaux suivants."""
    refresh = Refresh(setup)
    a, b = setup.clinicians
    refresh.rules.save(rule(a, weekday=1, start=time(9), end=time(10), step_minutes=30))
    refresh.rules.save(rule(b, weekday=1, start=time(14), end=time(15), step_minutes=60))
    refresh(a)
    refresh(b)
    refresh.rules.rows.clear()

    refresh(a)

    assert starts(setup, setup.types[0], (a, b)) == [paris(23, 14)]


def test_a_department_read_gives_every_clinicians_starts_in_order_with_their_clinician(
    setup: Setup,
) -> None:
    """Décision du plan : la lecture garde le praticien de chaque créneau, sans dédoublonner."""
    refresh = Refresh(setup)
    a, b = setup.clinicians
    refresh.rules.save(rule(a, weekday=1, start=time(10), end=time(11), step_minutes=30))
    refresh.rules.save(rule(b, weekday=1, start=time(9), end=time(10, 30), step_minutes=30))
    refresh(a)
    refresh(b)

    found = setup.queries.free_slots(
        setup.types[0], (a, b), within=Period(paris(23, 0), paris(24, 0)), not_before=NOW
    )

    assert [f.slot.start for f in found] == [
        paris(23, 9),
        paris(23, 9, 30),
        paris(23, 10),
        paris(23, 10),
        paris(23, 10, 30),
    ]
    assert {(f.clinician_id, f.slot.start) for f in found if f.slot.start == paris(23, 10)} == {
        (a, paris(23, 10)),
        (b, paris(23, 10)),
    }
    assert starts(setup, setup.types[0], (a,)) == [paris(23, 10), paris(23, 10, 30)]


def test_starts_already_past_are_never_read(setup: Setup) -> None:
    """Décision du plan : le passé est filtré à la lecture, jamais laissé au job."""
    refresh = Refresh(setup)
    a = setup.clinicians[0]
    refresh.rules.save(rule(a, weekday=1, start=time(9), end=time(10), step_minutes=30))
    refresh(a)

    assert starts(setup, setup.types[0], (a,), not_before=paris(23, 9, 15)) == [paris(23, 9, 30)]
