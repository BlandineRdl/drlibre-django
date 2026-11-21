from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_session, stored_user
from tests.integration.bookable import SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


def booked(world: Bookable, client: Client) -> Appointment:
    patient = stored_user(Role.PATIENT, password=None)
    client.cookies[COOKIE] = stored_session(patient)
    return world.app().book_appointment.execute(
        patient_id=patient.id,
        appointment_type_id=world.scene.kind,
        clinician_id=world.clinician,
        start=SLOT_START,
    )


def post(client: Client, appointment: Appointment, action: str, body: dict[str, Any]) -> Any:
    url = f"/api/v1/appointments/{appointment.id}/{action}"
    return client.post(url, body, content_type="application/json")


def test_a_patient_cancels_through_the_api_and_it_is_stored(
    client: Client, world: Bookable
) -> None:
    """Story « annule » : POST /appointments/{id}/cancel applique les mêmes règles."""
    appointment = booked(world, client)

    response = post(client, appointment, "cancel", {"reason": "  Empêchement  "})

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    stored = DjangoAppointments().get(appointment.id)
    assert stored is not None
    assert (stored.status, stored.cancellation_reason) == (
        AppointmentStatus.CANCELLED,
        "Empêchement",
    )


def test_a_patient_moves_through_the_api_to_a_free_slot_with_the_end_recomputed(
    client: Client, world: Bookable
) -> None:
    """Story « déplace » : POST /appointments/{id}/reschedule, fin jamais reçue."""
    appointment = booked(world, client)

    with_end = post(
        client,
        appointment,
        "reschedule",
        {"start": "2026-11-23T09:00:00Z", "end": "2026-11-23T11:00:00Z"},
    )
    moved = post(client, appointment, "reschedule", {"start": "2026-11-23T09:00:00Z"})
    taken = post(client, appointment, "reschedule", {"start": "2026-11-23T09:15:00Z"})

    assert with_end.status_code == 400
    assert moved.status_code == 200
    assert (moved.json()["start"], moved.json()["end"]) == (
        "2026-11-23T09:00:00+00:00",
        "2026-11-23T09:30:00+00:00",
    )
    assert taken.status_code == 422
    assert taken.json()["details"]["rules"] == ["outside_availability"]


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN], ids=["no-profile", "admin"])
def test_an_admin_or_a_stranger_cannot_change_a_patients_appointment(
    client: Client, world: Bookable, role: Role
) -> None:
    """§14 : seuls le patient et son praticien agissent ; l'admin attend E7."""
    appointment = booked(world, client)
    staff = Client()
    staff.cookies[COOKIE] = stored_session(stored_user(role))

    refused = [
        post(staff, appointment, "cancel", {"reason": "x"}),
        post(staff, appointment, "reschedule", {"start": "2026-11-23T09:00:00Z"}),
        post(staff, appointment, "check-in", {}),
    ]
    anonymous = post(Client(), appointment, "cancel", {"reason": "x"})

    assert [(r.status_code, r.json()["code"]) for r in refused] == [(403, "forbidden")] * 3
    assert anonymous.status_code == 401


def test_a_patient_cannot_name_another_patient_or_a_room_when_booking(
    client: Client, world: Bookable
) -> None:
    """Règle §5.4 : un patient ne choisit ni le patient ni la salle (forbidden)."""
    patient = stored_user(Role.PATIENT, password=None)
    client.cookies[COOKIE] = stored_session(patient)
    body = {"type": str(world.scene.kind), "start": SLOT_START.isoformat()}

    other = client.post(
        "/api/v1/appointments", {**body, "patient": str(Id())}, content_type="application/json"
    )
    room = client.post(
        "/api/v1/appointments",
        {**body, "room": str(world.scene.room)},
        content_type="application/json",
    )

    assert [(r.status_code, r.json()["code"]) for r in (other, room)] == [(403, "forbidden")] * 2
