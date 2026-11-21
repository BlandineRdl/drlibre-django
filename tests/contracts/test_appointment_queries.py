from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.application.ports.inbound import AppointmentQueries
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import stored_scene
from tests.fakes.booking import InMemoryAppointmentQueries, InMemoryAppointments

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass
class Scene:
    queries: AppointmentQueries
    store: DjangoAppointments | InMemoryAppointments
    clinician: Id
    clinician_user: Id
    kind: Id
    room: Id | None


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        store = InMemoryAppointments()
        queries = InMemoryAppointmentQueries(store)
        clinician, user = Id(), Id()
        queries.clinician_users[clinician] = user
        return Scene(queries, store, clinician, user, Id(), Id())
    stored = stored_scene()
    profile = stored.clinicians[0]
    return Scene(
        DjangoBookingQueries(),
        DjangoAppointments(),
        profile.id,
        profile.user_id,
        stored.kind,
        stored.room,
    )


def book(
    scene: Scene,
    start: datetime,
    *,
    patient: Id | None = None,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Id:
    appointment = Appointment(
        id=Id(),
        patient_id=patient or Id(),
        clinician_id=scene.clinician,
        appointment_type_id=scene.kind,
        room_id=scene.room,
        start=start,
        end=start + timedelta(minutes=30),
        status=status,
        source=Source.ONLINE,
    )
    scene.store.add(appointment)
    return appointment.id


def test_appointments_of_a_type_a_room_or_a_clinician_block_their_deletion(scene: Scene) -> None:
    """Story référentiel : un élément encore utilisé par des rendez-vous ne se supprime pas."""
    first = book(scene, NOW + timedelta(days=1))
    second = book(scene, NOW + timedelta(days=2), status=AppointmentStatus.CANCELLED)

    for found in (
        scene.queries.dependents_of_type(scene.kind),
        scene.queries.dependents_of_room(scene.room) if scene.room else (),
        scene.queries.dependents_of_clinician(scene.clinician),
    ):
        assert [(d.kind, d.id) for d in found] == [("appointment", first), ("appointment", second)]
    assert scene.queries.dependents_of_type(Id()) == ()
    assert scene.queries.dependents_of_clinician(Id()) == ()


def test_a_clinician_user_is_blocked_by_active_upcoming_appointments_only(scene: Scene) -> None:
    """Story utilisateurs : un praticien aux rendez-vous actifs à venir ne se désactive pas."""
    active = book(scene, NOW + timedelta(days=1))
    book(scene, NOW + timedelta(days=2), status=AppointmentStatus.NO_SHOW)
    book(scene, NOW - timedelta(days=1))

    found = scene.queries.active_upcoming_for_clinician_user(scene.clinician_user, after=NOW)

    assert [d.id for d in found] == [active]
    assert scene.queries.active_upcoming_for_clinician_user(Id(), after=NOW) == ()


def test_a_patient_or_a_clinician_user_with_any_appointment_cannot_be_deleted(
    scene: Scene,
) -> None:
    """Story utilisateurs : un compte lié à des rendez-vous ne se supprime pas."""
    patient = Id()
    booked = book(
        scene, NOW - timedelta(days=3), patient=patient, status=AppointmentStatus.COMPLETED
    )

    assert [d.id for d in scene.queries.any_for_user(patient)] == [booked]
    assert [d.id for d in scene.queries.any_for_user(scene.clinician_user)] == [booked]
    assert scene.queries.any_for_user(Id()) == ()


def test_booked_periods_come_back_with_their_status(scene: Scene) -> None:
    """Décision du plan : les créneaux lisent les périodes et statuts des rendez-vous."""
    book(scene, NOW + timedelta(days=1))
    book(scene, NOW + timedelta(days=5), status=AppointmentStatus.CANCELLED)

    found = scene.queries.periods_of(scene.clinician, start=NOW, end=NOW + timedelta(days=2))

    assert [(p.start, p.status) for p in found] == [
        (NOW + timedelta(days=1), AppointmentStatus.BOOKED)
    ]
