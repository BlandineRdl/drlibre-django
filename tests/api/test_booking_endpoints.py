import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
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


def post(client: Client, url: str, body: dict[str, object]) -> Any:
    return client.post(url, json.dumps(body), content_type="application/json")


def hold_body(world: Bookable, **changes: object) -> dict[str, object]:
    visitor = {k: v for k, v in world.visitor().items() if k != "network"}
    return {
        "type": str(world.scene.kind),
        "clinician": str(world.clinician),
        "start": SLOT_START.isoformat(),
        **visitor,
        **changes,
    }


def test_an_anonymous_visitor_holds_then_verifies_without_any_session_before_the_code(
    client: Client, world: Bookable
) -> None:
    """Story réservation : POST /booking/holds puis /verify, même parcours sans session."""
    body = hold_body(world)

    held = post(client, "/api/v1/booking/holds", body)

    assert held.status_code == 201
    assert COOKIE not in held.cookies
    assert set(held.json()) == {"hold_id", "provider_id", "expires_at"}
    assert body["email"] not in held.content.decode()

    verified = post(
        client, f"/api/v1/booking/holds/{held.json()['hold_id']}/verify", {"code": world.code()}
    )

    assert verified.status_code == 200
    assert verified.json()["appointment"]["start"].startswith("2026-11-23T08:00")
    assert COOKIE in verified.cookies


def test_a_correct_code_with_a_failed_placement_answers_the_error_and_still_opens_the_session(
    client: Client, world: Bookable
) -> None:
    """Story placement en échec : le code est correct, échec au statut du code, session ouverte."""
    held = post(client, "/api/v1/booking/holds", hold_body(world))
    DjangoAppointments().add(
        Appointment.book(
            patient_id=stored_user(Role.PATIENT).id,
            clinician_id=world.clinician,
            appointment_type_id=world.scene.kind,
            room_id=None,
            start=SLOT_START,
            duration=timedelta(minutes=30),
            source=Source.STAFF,
        )
    )

    response = post(
        client, f"/api/v1/booking/holds/{held.json()['hold_id']}/verify", {"code": world.code()}
    )

    assert response.status_code == 409
    assert set(response.json()) == {"code", "message", "details"}
    assert response.json()["code"] == "conflict"
    assert COOKIE in response.cookies


def test_a_wrong_code_is_refused_as_invalid_on_the_code_field(
    client: Client, world: Bookable
) -> None:
    """Story réservation : un code incorrect est refusé, rien n'est réservé."""
    held = post(client, "/api/v1/booking/holds", hold_body(world))

    response = post(
        client, f"/api/v1/booking/holds/{held.json()['hold_id']}/verify", {"code": "000000"}
    )

    assert response.status_code == 400
    assert response.json()["details"]["fields"][0]["field"] == "code"
    assert COOKIE not in response.cookies


def test_an_end_time_or_an_unknown_field_is_refused_as_invalid_input(
    client: Client, world: Bookable
) -> None:
    """Règle §5.2 : l'heure de fin n'est jamais acceptée de l'appelant."""
    response = post(client, "/api/v1/booking/holds", hold_body(world, end=SLOT_START.isoformat()))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"
    assert response.json()["details"]["fields"][0]["field"] == "end"


def test_a_fourth_code_request_within_the_hour_is_refused_as_too_many_requests(
    client: Client, world: Bookable
) -> None:
    """Story limites : au plus 3 renvois de code par heure et par email."""
    held = post(client, "/api/v1/booking/holds", hold_body(world))
    url = f"/api/v1/booking/holds/{held.json()['hold_id']}/resend"

    statuses = [client.post(url).status_code for _ in range(4)]
    refused = client.post(url)

    assert statuses[:3] == [204, 204, 204]
    assert statuses[3] == 422
    assert refused.json()["details"] == {"rules": ["too_many_requests"]}


def test_a_fourth_hold_for_the_same_email_within_the_hour_is_refused(
    client: Client, world: Bookable
) -> None:
    """Story limites : au plus 3 réservations provisoires par heure et par email."""
    body = hold_body(world)

    statuses = [post(client, "/api/v1/booking/holds", body).status_code for _ in range(4)]

    assert statuses == [201, 201, 201, 422]


def test_booking_as_a_patient_needs_a_session_and_refuses_an_end_time(
    client: Client, world: Bookable
) -> None:
    """Story patient connecté : POST /appointments exige la session, sans heure de fin."""
    anonymous = post(
        client,
        "/api/v1/appointments",
        {"type": str(world.scene.kind), "start": SLOT_START.isoformat()},
    )
    held = post(client, "/api/v1/booking/holds", hold_body(world))
    post(client, f"/api/v1/booking/holds/{held.json()['hold_id']}/verify", {"code": world.code()})
    later = {"type": str(world.scene.kind), "clinician": str(world.clinician)}

    with_end = post(
        client,
        "/api/v1/appointments",
        {**later, "start": SLOT_START.isoformat(), "end": SLOT_START.isoformat()},
    )
    other_start = SLOT_START.replace(hour=9)
    booked = post(client, "/api/v1/appointments", {**later, "start": other_start.isoformat()})

    assert anonymous.status_code == 401
    assert with_end.status_code == 400
    assert booked.status_code == 201
    assert booked.json()["start"].startswith("2026-11-23T09:00")


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN], ids=["clinician", "admin"])
def test_a_signed_in_staff_member_cannot_book_through_the_api(
    client: Client, world: Bookable, role: Role
) -> None:
    """Règle §7.1 : le personnel connecté ne réserve pas par l'API (forbidden)."""
    client.cookies[COOKIE] = stored_session(stored_user(role))

    refused = post(
        client,
        "/api/v1/appointments",
        {"type": str(world.scene.kind), "start": SLOT_START.isoformat()},
    )

    assert refused.status_code == 403
