from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_session, stored_user
from tests.integration.bookable import SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
URL = "/api/v1/appointments"


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


def signed_in(user: User) -> Client:
    client = Client()
    client.cookies[COOKIE] = stored_session(user)
    return client


def clinician(world: Bookable, index: int = 0) -> Client:
    user = DjangoUsers().get(world.scene.clinicians[index].user_id)
    assert user is not None
    return signed_in(user)


def booked(world: Bookable, start: Any = SLOT_START) -> tuple[User, Appointment]:
    patient = stored_user(Role.PATIENT, password=None)
    appointment = world.app().book_appointment.execute(
        patient_id=patient.id,
        appointment_type_id=world.scene.kind,
        clinician_id=world.clinician,
        start=start,
    )
    return patient, appointment


def post(client: Client, url: str, body: dict[str, Any] | None = None) -> Any:
    return client.post(url, body or {}, content_type="application/json")


def act(client: Client, appointment: Appointment, action: str, body: Any = None) -> Any:
    return post(client, f"{URL}/{appointment.id}/{action}", body)


def test_the_clinician_checks_in_completes_and_marks_absent_through_the_api(
    world: Bookable,
) -> None:
    """Story « statut » : POST /appointments/{id}/check-in, /complete et /no-show (§14)."""
    _, first = booked(world)
    _, second = booked(world, SLOT_START + timedelta(minutes=30))
    own = clinician(world)

    checked_in = act(own, first, "check-in")
    completed = act(own, first, "complete")
    again = act(own, first, "check-in")
    absent = act(own, second, "no-show")

    assert [r.json()["status"] for r in (checked_in, completed, absent)] == [
        "CHECKED_IN",
        "COMPLETED",
        "NO_SHOW",
    ]
    assert again.status_code == 409
    assert (again.json()["code"], again.json()["details"]) == (
        "invalid_transition",
        {"status": "COMPLETED"},
    )


def test_the_clinician_cancels_with_a_reason_through_the_api_and_the_patient_is_notified(
    world: Bookable,
) -> None:
    """Story « annule » : l'annulation est aussi disponible par POST .../cancel (§14)."""
    patient, appointment = booked(world)
    notified = NotificationRecord.objects.filter(recipient_id=patient.id.value)
    before = notified.count()

    response = act(clinician(world), appointment, "cancel", {"reason": "Praticien absent"})

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert notified.count() == before + 1


def test_the_clinician_moves_an_appointment_through_the_api(world: Bookable) -> None:
    """Story « déplace » : le déplacement est aussi disponible par POST .../reschedule (§14)."""
    _, appointment = booked(world)
    target = SLOT_START + timedelta(hours=1)

    response = act(clinician(world), appointment, "reschedule", {"start": target.isoformat()})

    assert response.status_code == 200
    assert (response.json()["start"], response.json()["end"]) == (
        target.isoformat(),
        (target + timedelta(minutes=30)).isoformat(),
    )


def test_the_clinician_books_a_patient_in_their_own_calendar_as_staff(world: Bookable) -> None:
    """Story « réserve par l'API » : RDV `BOOKED`, source `STAFF`, dans l'agenda du praticien."""
    patient = stored_user(Role.PATIENT, password=None)
    body = {"patient": str(patient.id), "type": str(world.scene.kind)}

    response = post(clinician(world), URL, {**body, "start": SLOT_START.isoformat()})

    assert response.status_code == 201
    assert (response.json()["status"], response.json()["clinician"]) == (
        "BOOKED",
        str(world.clinician),
    )
    stored = DjangoAppointments().get(Id.parse(response.json()["id"]))
    assert stored is not None
    assert (stored.patient_id, stored.source) == (patient.id, Source.STAFF)


def test_a_clinicians_booking_must_name_a_patient_and_no_other_clinician_nor_an_end(
    world: Bookable,
) -> None:
    """Story « réserve par l'API » : patient requis, autre praticien refusé, fin jamais reçue."""
    patient = stored_user(Role.PATIENT, password=None)
    own = clinician(world)
    body = {"type": str(world.scene.kind), "start": SLOT_START.isoformat()}
    other = str(world.scene.clinicians[1].id)

    no_patient = post(own, URL, body)
    other_clinician = post(own, URL, {**body, "patient": str(patient.id), "clinician": other})
    with_end = post(own, URL, {**body, "patient": str(patient.id), "end": SLOT_START.isoformat()})

    assert (no_patient.status_code, no_patient.json()["code"]) == (400, "invalid_input")
    assert (other_clinician.status_code, other_clinician.json()["code"]) == (403, "forbidden")
    assert with_end.status_code == 400


def test_the_clinician_lists_only_their_own_appointments_without_notes(world: Bookable) -> None:
    """Story « agenda du jour » : `GET /appointments` ne lui renvoie que les siens."""
    _, mine = booked(world)
    other = world.app().book_appointment.execute(
        patient_id=stored_user(Role.PATIENT, password=None).id,
        appointment_type_id=world.scene.kind,
        clinician_id=world.scene.clinicians[1].id,
        start=SLOT_START + timedelta(minutes=30),
    )
    own = clinician(world)
    act(own, mine, "check-in")
    world.app().write_clinical_notes.execute(
        actor_id=world.scene.clinicians[0].user_id, appointment_id=mine.id, text="Tension normale"
    )

    response = own.get(URL, {"clinician": str(other.clinician_id)})

    assert response.status_code == 200
    (entry,) = response.json()["appointments"]
    assert (entry["id"], entry["status"], entry["allowed_actions"]) == (
        str(mine.id),
        "CHECKED_IN",
        ["cancel", "complete"],
    )
    assert "Tension normale" not in response.content.decode()


def test_another_clinicians_appointment_is_forbidden_through_the_api(world: Bookable) -> None:
    """Story « fiche » : le RDV d'un autre praticien n'est ni lu ni changé (forbidden)."""
    _, appointment = booked(world)
    stranger = clinician(world, 1)

    responses = [
        act(stranger, appointment, "check-in"),
        act(stranger, appointment, "cancel", {"reason": "x"}),
        act(stranger, appointment, "reschedule", {"start": SLOT_START.isoformat()}),
    ]

    assert [(r.status_code, r.json()["code"]) for r in responses] == [(403, "forbidden")] * 3


def test_a_cross_origin_status_change_is_refused(world: Bookable) -> None:
    """Règle §16 : une requête d'une autre origine est refusée avant tout changement."""
    _, appointment = booked(world)

    response = clinician(world).post(
        f"{URL}/{appointment.id}/check-in", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    stored = DjangoAppointments().get(appointment.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.BOOKED
