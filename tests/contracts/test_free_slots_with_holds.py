from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.application.ports.outbound import FreeSlots
from drlibre.booking.application.use_cases.open_holds import OpenHoldsUseCase
from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.infrastructure.free_slots import SchedulingFreeSlots
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import DjangoHolds
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.scheduling.application.ports.outbound import StoredSlot
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation
from drlibre.scheduling.application.use_cases.free_clinicians_at import FreeCliniciansAtUseCase
from drlibre.scheduling.application.use_cases.is_slot_free import IsSlotFreeUseCase
from drlibre.scheduling.domain.slot import Slot
from drlibre.scheduling.infrastructure.booking_appointments import BookingClinicianAppointments
from drlibre.scheduling.infrastructure.booking_holds import BookingSlotHolds
from drlibre.scheduling.infrastructure.directory import OrganisationSchedulingDirectory
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.scheduling.infrastructure.slot_queries import DjangoSlotQueries
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import stored_scene
from tests.fakes.booking import InMemoryFreeSlots, InMemoryHolds
from tests.fakes.clock import FixedClock

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
START = NOW + timedelta(days=1)
DURATION = timedelta(minutes=30)
BUFFER = timedelta(minutes=15)


@dataclass
class Scene:
    free_slots: FreeSlots
    first: Id
    second: Id
    kind: Id
    list_slot: Callable[[Id, datetime], None]
    hold: Callable[[Id, datetime, datetime], Id]


def visitor() -> VisitorDetails:
    return VisitorDetails("Ana Martin", date(1990, 5, 17), "ana@example.org", None, None)


def opened(clinician: Id, kind: Id, start: datetime, at: datetime) -> BookingHold:
    return BookingHold.open(
        clinician_id=clinician,
        appointment_type_id=kind,
        start=start,
        duration=DURATION,
        source=Source.ONLINE,
        details=visitor(),
        at=at,
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        holds = InMemoryHolds()
        fake = InMemoryFreeSlots(holds, FixedClock(NOW))
        first, second, kind = Id(), Id(), Id()
        fake.durations[kind] = DURATION
        fake.buffers[kind] = BUFFER

        def list_slot(clinician: Id, start: datetime) -> None:
            fake.free.add((clinician, kind, start))

        def hold(clinician: Id, start: datetime, at: datetime) -> Id:
            made = opened(clinician, kind, start, at)
            holds.add(made)
            return made.id

        return Scene(fake, first, second, kind, list_slot, hold)

    stored = stored_scene(buffer_minutes=15, duration_minutes=30)
    first, second = stored.clinicians[0].id, stored.clinicians[1].id
    listed: dict[Id, list[StoredSlot]] = {first: [], second: []}

    def list_stored(clinician: Id, start: datetime) -> None:
        listed[clinician].append(StoredSlot(clinician, stored.kind, Slot(start, start + DURATION)))
        DjangoSlotStore().replace(clinician, tuple(listed[clinician]))

    def store_hold(clinician: Id, start: datetime, at: datetime) -> Id:
        made = opened(clinician, stored.kind, start, at)
        DjangoHolds().add(made)
        return made.id

    ports = {
        "clock": FixedClock(NOW),
        "directory": OrganisationSchedulingDirectory(
            queries=DjangoReferenceQueries(), lookup=DjangoUserQueries()
        ),
        "queries": DjangoSlotQueries(),
        "holds": BookingSlotHolds(OpenHoldsUseCase(holds=DjangoHolds())),
    }
    computation = SlotComputation(
        directory=ports["directory"],
        rules=DjangoAvailabilityRules(),
        time_offs=DjangoTimeOffs(),
        appointments=BookingClinicianAppointments(DjangoBookingQueries()),
    )
    real = SchedulingFreeSlots(
        IsSlotFreeUseCase(**ports, computation=computation), FreeCliniciansAtUseCase(**ports)
    )
    return Scene(real, first, second, stored.kind, list_stored, store_hold)


def test_a_listed_slot_is_free_for_its_clinician_only(scene: Scene) -> None:
    """Décision du plan : seul un créneau affiché est réservable, pour son praticien."""
    scene.list_slot(scene.first, START)

    assert scene.free_slots.is_free(scene.first, scene.kind, START, ignoring_hold=None)
    assert not scene.free_slots.is_free(scene.second, scene.kind, START, ignoring_hold=None)
    assert not scene.free_slots.is_free(
        scene.first, scene.kind, START + timedelta(minutes=5), ignoring_hold=None
    )
    assert scene.free_slots.candidates_at(scene.kind, START) == (scene.first,)


def test_an_open_hold_hides_the_slot_of_its_clinician_unless_it_is_the_ignored_hold(
    scene: Scene,
) -> None:
    """Story réservation provisoire : un créneau gardé n'est plus proposé à un autre."""
    scene.list_slot(scene.first, START)
    scene.list_slot(scene.second, START)
    held = scene.hold(scene.first, START, NOW)

    assert not scene.free_slots.is_free(scene.first, scene.kind, START, ignoring_hold=None)
    assert scene.free_slots.is_free(scene.first, scene.kind, START, ignoring_hold=held)
    assert scene.free_slots.is_free(scene.second, scene.kind, START, ignoring_hold=None)
    assert scene.free_slots.candidates_at(scene.kind, START) == (scene.second,)


def test_a_hold_also_hides_the_slots_its_type_buffer_reaches(scene: Scene) -> None:
    """Décision du plan : la garde est prolongée de la pause du type du créneau."""
    before, touching, within_buffer, after_buffer = (
        START - timedelta(minutes=30),
        START - timedelta(minutes=15),
        START + timedelta(minutes=30),
        START + timedelta(minutes=45),
    )
    for slot in (before, touching, within_buffer, after_buffer):
        scene.list_slot(scene.first, slot)
    scene.hold(scene.first, START, NOW)

    def free(at: datetime) -> bool:
        return scene.free_slots.is_free(scene.first, scene.kind, at, ignoring_hold=None)

    assert free(before)
    assert not free(touching)
    assert not free(within_buffer)
    assert free(after_buffer)


def test_an_expired_hold_frees_the_slot_without_any_job(scene: Scene) -> None:
    """Décision du plan : l'expiration d'une garde libère le créneau à la lecture."""
    scene.list_slot(scene.first, START)
    scene.hold(scene.first, START, NOW - timedelta(minutes=11))

    assert scene.free_slots.is_free(scene.first, scene.kind, START, ignoring_hold=None)
    assert scene.free_slots.candidates_at(scene.kind, START) == (scene.first,)
