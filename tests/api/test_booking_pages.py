import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest
from django.conf import settings
from django.test import Client

from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
from tests.builders import stored_session, stored_user
from tests.integration.bookable import NOW, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
DETAILS = {
    "full_name": "Ana Martin",
    "birth_date": "1990-05-17",
    "phone": "",
    "reason": "Douleur",
    "accepted_terms": "on",
}


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


def slot_url(world: Bookable, *, first_available: bool = False, hour: int = 8) -> str:
    start = f"2026-11-23T{hour:02}:00:00Z"
    who = (
        f"department={world.scene.department}"
        if first_available
        else f"clinician={world.clinician}"
    )
    return f"/booking/new?type={world.scene.kind}&{who}&start={start}"


def submit(
    client: Client,
    world: Bookable,
    fields: dict[str, str],
    *,
    hour: int = 8,
    first_available: bool = False,
    headers: dict[str, str] | None = None,
) -> Any:
    """Post what the booking form posts: its hidden slot fields and what was typed."""
    url = slot_url(world, first_available=first_available, hour=hour)
    slot = dict(parse_qsl(urlsplit(url).query))
    return client.post("/booking/new", {**slot, **fields}, headers=headers or {})


def visit(client: Client, world: Bookable, *, first_available: bool = False) -> tuple[str, str]:
    """A visitor submits the details; returns the hold page and the emailed code."""
    email = str(world.visitor()["email"])
    response = submit(client, world, {**DETAILS, "email": email}, first_available=first_available)
    assert response.status_code == 302, response.content.decode()
    return response["Location"], world.code()


def book_through_the_flow(client: Client, world: Bookable) -> str:
    hold_url, code = visit(client, world)
    done = client.post(hold_url, {"code": code})
    assert done.status_code == 302
    return done["Location"]


def test_a_cross_origin_post_to_the_booking_pages_is_refused(
    client: Client, world: Bookable
) -> None:
    """Règle §12.3 : un POST venu d'un autre site est refusé, sans réservation provisoire."""
    hostile = {"Origin": "https://evil.example"}

    new = submit(client, world, {**DETAILS, "email": "a@example.org"}, headers=hostile)
    hold_url, _ = visit(client, world)
    verify = client.post(hold_url, {"code": world.code()}, headers=hostile)

    assert new.status_code == verify.status_code == 403


def test_the_booking_form_rejects_a_post_without_its_csrf_token(world: Bookable) -> None:
    """Règle §12.3 : les formulaires web gardent la protection CSRF."""
    strict = Client(enforce_csrf_checks=True)

    response = submit(strict, world, {**DETAILS, "email": "a@example.org"})

    assert response.status_code == 403


def test_a_visitor_books_in_three_steps_and_lands_on_a_confirmation_with_a_calendar_file(
    client: Client, world: Bookable
) -> None:
    """Story réservation : détails, code, puis confirmation avec .ics et lien vers /portal/."""
    details = client.get(slot_url(world))
    assert details.status_code == 200
    assert 'aria-current="step"' in details.content.decode()

    confirmation_url = book_through_the_flow(client, world)
    page = client.get(confirmation_url)

    body = page.content.decode()
    assert page.status_code == 200
    assert "Rendez-vous réservé" in body
    assert 'href="/portal/"' in body
    assert "Europe/Paris" in body
    assert client.cookies[COOKIE].value
    ics = client.get(f"{confirmation_url}.ics")
    assert ics.status_code == 200
    assert ics["Content-Type"].startswith("text/calendar")
    assert "DTSTART:20261123T080000Z\r\n" in ics.content.decode()


def test_the_calendar_file_is_only_for_its_own_patient(client: Client, world: Bookable) -> None:
    """Story réservation : .ics réservé à son patient, forbidden pour les autres."""
    confirmation_url = book_through_the_flow(client, world)
    stranger = Client()
    stranger.cookies[COOKIE] = stored_session(stored_user(Role.PATIENT))

    anonymous = Client().get(f"{confirmation_url}.ics")
    refused = stranger.get(f"{confirmation_url}.ics")
    page_refused = stranger.get(confirmation_url)

    assert anonymous.status_code == 302
    assert refused.status_code == page_refused.status_code == 403


def test_invalid_details_show_errors_tied_to_fields_with_focus_on_the_first(
    client: Client, world: Bookable
) -> None:
    """Story réservation : erreurs rattachées aux champs, focus sur le premier invalide."""
    response = submit(client, world, {"full_name": "", "email": "nope"})

    body = response.content.decode()
    assert response.status_code == 400
    assert re.search(r'id="field-full_name"[^>]*aria-invalid="true"[^>]*autofocus', body)
    assert 'aria-describedby="error-email"' in body


def test_a_wrong_code_keeps_the_hold_and_focuses_the_code_field_then_a_resend_sends_a_new_one(
    client: Client, world: Bookable
) -> None:
    """Story réservation : code incorrect, erreur sur le champ ; renvoi d'un nouveau code."""
    hold_url, first = visit(client, world)

    wrong = client.post(hold_url, {"code": "000000" if first != "000000" else "111111"})
    resent = client.post(f"{hold_url}/resend")
    again = client.get(resent["Location"])

    assert wrong.status_code == 400
    assert re.search(
        r'id="field-code"[^>]*aria-invalid="true"[^>]*autofocus', wrong.content.decode()
    )
    assert "Créneau tenu jusqu&#x27;à 11:10" in wrong.content.decode()
    assert "Un nouveau code vient d&#x27;être envoyé." in again.content.decode()


def test_a_slot_taken_meanwhile_shows_a_message_and_the_refreshed_slots(
    client: Client, world: Bookable
) -> None:
    """Story règle enfreinte : créneau pris entre-temps, message et créneaux rafraîchis."""
    book_through_the_flow(Client(), world)

    response = submit(client, world, {**DETAILS, "email": str(world.visitor()["email"])})

    body = response.content.decode()
    assert response.status_code == 409
    assert 'role="alert"' in body
    assert "start=2026-11-23T08:30:00Z" in body
    assert "start=2026-11-23T08:00:00Z" not in body


def test_an_expired_hold_says_so_and_offers_the_slots_again(
    client: Client, world: Bookable
) -> None:
    """Story réservations provisoires limitées : hold expiré, message et créneaux libres."""
    hold_url, code = visit(client, world)
    use_container(world.app(NOW.replace(hour=10, minute=11)))

    response = client.post(hold_url, {"code": code})

    assert response.status_code == 404
    assert "expiré" in response.content.decode()
    assert "start=2026-11-23T08:00:00Z" in response.content.decode()


def test_a_first_available_booking_names_the_chosen_provider_on_the_code_page(
    client: Client, world: Bookable
) -> None:
    """Story premier disponible : le praticien retenu est nommé sur la page du code."""
    details = client.get(slot_url(world, first_available=True))
    hold_url, code = visit(client, world, first_available=True)
    code_page = client.get(hold_url)
    done = client.post(hold_url, {"code": code})

    assert "Premier praticien disponible" in details.content.decode()
    assert "Premier praticien disponible" not in code_page.content.decode()
    assert done.status_code == 302


def test_a_signed_in_patient_confirms_without_retyping_their_details(
    client: Client, world: Bookable
) -> None:
    """Story patient connecté : le choix mène à la confirmation, sans formulaire d'informations."""
    book_through_the_flow(client, world)
    emails_before = len(world.outbox.queued)

    choice = client.get(slot_url(world, hour=9))
    booked = submit(client, world, {}, hour=9)

    assert "Confirmer le rendez-vous" in choice.content.decode()
    assert 'name="full_name"' not in choice.content.decode()
    assert booked.status_code == 302
    assert booked["Location"].startswith("/booking/appointments/")
    assert len(world.outbox.queued) == emails_before + 1
    assert world.outbox.queued[-1].subject == "Confirmation de votre rendez-vous"


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN], ids=["clinician", "admin"])
def test_a_signed_in_staff_member_cannot_book_through_the_flow(
    client: Client, world: Bookable, role: Role
) -> None:
    """Règle §7.1 : le personnel connecté ne réserve pas par ce parcours (forbidden)."""
    client.cookies[COOKIE] = stored_session(stored_user(role))

    get = client.get(slot_url(world))
    post = submit(client, world, {})

    assert get.status_code == post.status_code == 403
