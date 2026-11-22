from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.repositories import DjangoWaitlist
from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import (
    AppointmentResponseFilter,
    AppointmentResponseQueries,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_appointment_responses import (
    SqlAppointmentResponseQueries,
)
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_booking import stored_scene
from tests.fakes.world import FakeWorld

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Scene:
    """Anne accepted one offer and still waits for another; Bruno accepted one."""

    anne: Id
    bruno: Id
    ids: dict[str, Id]


def _entry(patient_id: Id, kind: Id, status: WaitlistStatus) -> WaitlistEntry:
    return WaitlistEntry(
        id=Id(),
        patient_id=patient_id,
        appointment_type_id=kind,
        clinician_id=None,
        earliest=NOW + timedelta(days=3),
        latest=NOW + timedelta(days=4),
        status=status,
        created_at=NOW,
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def responses(request: pytest.FixtureRequest) -> tuple[AppointmentResponseQueries, Scene]:
    if request.param == "fake":
        world = FakeWorld()
        port, add, kind = world.app.appointment_responses, world.waitlist.add, Id()
        anne, bruno = Id(), Id()
    else:
        port, add, kind = SqlAppointmentResponseQueries(), DjangoWaitlist().add, stored_scene().kind
        anne, bruno = stored_user(Role.PATIENT).id, stored_user(Role.PATIENT).id
    scene = Scene(anne, bruno, {})
    for name, patient, status in (
        ("anne booked", anne, WaitlistStatus.BOOKED),
        ("anne waiting", anne, WaitlistStatus.WAITING),
        ("bruno booked", bruno, WaitlistStatus.BOOKED),
    ):
        entry = _entry(patient, kind, status)
        add(entry)
        scene.ids[name] = entry.id
    return port, scene


Fixture = tuple[AppointmentResponseQueries, Scene]


def _names(
    port: AppointmentResponseQueries,
    scene: Scene,
    reader: Reader,
    criteria: AppointmentResponseFilter = AppointmentResponseFilter(),  # noqa: B008
) -> list[str]:
    by_id = {i: name for name, i in scene.ids.items()}
    found = port.responses(criteria, reader).items
    return sorted(by_id[r.id] for r in found if r.id in by_id)


def test_a_patient_reads_only_their_own_accepted_offers(responses: Fixture) -> None:
    """Story liste d'attente FHIR: `AppointmentResponse` readable by the patient, their own."""
    port, scene = responses

    assert _names(port, scene, Reader(ReaderKind.PATIENT, scene.anne)) == ["anne booked"]
    assert _names(port, scene, Reader(ReaderKind.PATIENT, scene.bruno)) == ["bruno booked"]


def test_the_admin_reads_every_accepted_offer_and_others_none(responses: Fixture) -> None:
    """Story liste d'attente FHIR: the admin reads them all; a clinician or a visitor none."""
    port, scene = responses
    admin = Reader(ReaderKind.ADMIN, Id())

    assert _names(port, scene, admin) == ["anne booked", "bruno booked"]
    assert _names(port, scene, admin, AppointmentResponseFilter(patient=scene.bruno)) == [
        "bruno booked"
    ]
    assert _names(
        port, scene, admin, AppointmentResponseFilter(ids=(scene.ids["anne booked"],))
    ) == ["anne booked"]
    assert _names(port, scene, Reader(ReaderKind.CLINICIAN, Id(), Id())) == []
    assert _names(port, scene, Reader.anonymous()) == []


def test_only_accepted_offers_exist(responses: Fixture) -> None:
    """Spec §15.3: an `AppointmentResponse` is a booked entry, a waiting one is none."""
    port, scene = responses

    assert port.exists(scene.ids["anne booked"])
    assert not port.exists(scene.ids["anne waiting"])
    assert not port.exists(Id())
