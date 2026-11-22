"""Steps of the FHIR `Appointment` updates, each compared with the application API or a screen."""

import json
from datetime import datetime
from typing import Any

from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.booking.infrastructure.django.models import AppointmentRecord, WaitlistEntryRecord
from drlibre.bootstrap.container import container, use_container
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_session
from tests.fhir.appointment_steps import (
    _ABSENT,
    MONDAY,
    Booking,
    _at,
    _local,
    _parsed,
    _participants,
)
from tests.fhir.directory_steps import Exchange
from tests.integration.bookable import NOW, free_starts

_API_STATUS = {"checked-in": "check-in", "fulfilled": "complete", "noshow": "no-show"}


def _api_call(asked: dict[str, str], at: datetime | None) -> tuple[str, dict[str, Any] | None]:
    """The `POST /api/v1/appointments/{id}/…` action and body asking the same change."""
    if at is not None:
        return "reschedule", {"start": at.isoformat()}
    if asked.get("status") == "cancelled":
        return "cancel", {"reason": asked.get("reason", "")}
    return _API_STATUS.get(asked.get("status", ""), ""), None


def _resource(booking: Booking, who: str, appointment: Id, asked: dict[str, str]) -> Any:
    """The appointment as `who` reads it (an admin when `who` cannot), with the changes."""
    response = Client().get(f"/fhir/Appointment/{appointment}", headers=booking.headers(who))
    if response.status_code != 200:
        response = Client().get(
            f"/fhir/Appointment/{appointment}", headers=booking.headers("admin")
        )
    body = response.json()
    if "start" in asked:
        body["start"] = _at(asked["start"]).isoformat()
    if "status" in asked:
        body["status"] = asked["status"]
    if "reason" in asked:
        body["cancelationReason"] = {"text": asked["reason"]}
    if "comment" in asked:
        body["comment"] = asked["comment"]
    if "practitioner" in asked:
        others = [p for p in body["participant"] if "Practitioner/" not in p["actor"]["reference"]]
        practitioner = {"reference": f"Practitioner/{booking.user(asked['practitioner']).id}"}
        body["participant"] = [*others, {"actor": practitioner}]
    if asked.get("type") == "absent":
        body["serviceType"][0]["coding"][0]["code"] = str(_ABSENT)
    return body


def _update(
    booking: Booking, exchange: Exchange, who: str, owner: str, raw: str, stale: bool
) -> None:
    appointment, asked = booking.labels[owner], _parsed(raw)
    body = _resource(booking, who, appointment, asked)
    if stale:
        AppointmentRecord.objects.filter(id=appointment.value).update(reason="Relu ailleurs")
    at = _at(asked["start"]) if "start" in asked else None
    booking.asked = {"who": who, "appointment": appointment, "api": _api_call(asked, at)}
    exchange.response = Client().put(
        f"/fhir/Appointment/{appointment}",
        data=json.dumps(body),
        content_type="application/fhir+json",
        headers=booking.headers(who) | {"If-Match": f'W/"{body["meta"]["versionId"]}"'},
    )


@when(parsers.parse('"{who}" updates in FHIR the appointment of "{owner}" with "{raw}"'))
def updates_in_fhir(booking: Booking, exchange: Exchange, who: str, owner: str, raw: str) -> None:
    _update(booking, exchange, who, owner, raw, stale=False)


@when(
    parsers.parse(
        '"{who}" updates in FHIR the appointment of "{owner}" with "{raw}" at a stale version'
    )
)
def updates_stale(booking: Booking, exchange: Exchange, who: str, owner: str, raw: str) -> None:
    _update(booking, exchange, who, owner, raw, stale=True)


def _post_api(booking: Booking, who: str, appointment: Id, call: tuple[str, Any]) -> Any:
    action, body = call
    return Client().post(
        f"/api/v1/appointments/{appointment}/{action}",
        data=json.dumps(body) if body is not None else None,
        content_type="application/json",
        headers=booking.headers(who),
    )


@when(
    parsers.parse('"{who}" sends "{raw}" to the application API for the appointment of "{owner}"')
)
def sends_to_api(booking: Booking, who: str, raw: str, owner: str) -> None:
    asked = _parsed(raw)
    at = _at(asked["start"]) if "start" in asked else None
    response = _post_api(booking, who, booking.labels[owner], _api_call(asked, at))
    assert response.status_code == 200, response.content


@when(parsers.parse('"{who}" writes the notes "{text}" on the appointment file of "{owner}"'))
def writes_notes_on_screen(booking: Booking, who: str, text: str, owner: str) -> None:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(booking.user(who))
    path = f"/workspace/appointments/{booking.labels[owner]}/notes"
    response = client.post(path, {"clinical_notes": text})
    assert response.status_code == 302, response.content


@then("the application API answers the same to the same update")
def api_answers_the_same(booking: Booking, exchange: Exchange) -> None:
    asked = booking.asked
    replayed = _post_api(booking, asked["who"], asked["appointment"], asked["api"])
    issue = exchange.body()["issue"][0]
    code = issue["details"]["coding"][0]["code"]
    answer = replayed.json()
    assert (replayed.status_code, answer["code"]) == (exchange.response.status_code, code), answer
    # Field names are FHIR paths on one side, API names on the other; other details match.
    if code != "invalid_input":
        assert json.loads(issue.get("diagnostics", "{}")) == (answer["details"] or {})


def _updated(exchange: Exchange, status: str) -> dict[str, Any]:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    assert body["status"] == status
    return body


@then(parsers.parse('the update answers "{status}"'))
def update_answers(exchange: Exchange, status: str) -> None:
    _updated(exchange, status)


@then(parsers.parse('the update answers "{status}" at "{hhmm}" with "{clinician}" and the room'))
def update_moved(
    booking: Booking, exchange: Exchange, status: str, hhmm: str, clinician: str
) -> None:
    body = _updated(exchange, status)
    assert _local(body["start"]) == hhmm
    assert f"Practitioner/{booking.user(clinician).id}" in _participants(body)
    assert f"Location/{booking.world.scene.room}" in _participants(body)


@then(parsers.parse('the update answers "{status}" with the cancellation reason "{reason}"'))
def update_cancelled(exchange: Exchange, status: str, reason: str) -> None:
    assert _updated(exchange, status)["cancelationReason"] == {"text": reason}


@then(parsers.parse('the update answers "{status}" with the notes "{notes}"'))
def update_noted(exchange: Exchange, status: str, notes: str) -> None:
    assert _updated(exchange, status)["comment"] == notes


@then(parsers.parse('the refusal gives the current status "{status}"'))
def refusal_status(exchange: Exchange, status: str) -> None:
    assert json.loads(exchange.body()["issue"][0]["diagnostics"]) == {"status": status}


@then(parsers.parse('the refusal names the fields "{paths}"'))
def refusal_fields(exchange: Exchange, paths: str) -> None:
    expected = [p.strip() for p in paths.split(",")]
    assert exchange.body()["issue"][0]["expression"] == expected


@given(parsers.parse('the appointment of "{owner}" is "{status}"'))
def appointment_is(booking: Booking, owner: str, status: str) -> None:
    AppointmentRecord.objects.filter(id=booking.labels[owner].value).update(status=status)


@given(parsers.parse('the clock is at "{instant}"'))
def clock_at(booking: Booking, instant: str) -> None:
    use_container(booking.world.app(datetime.fromisoformat(instant)))


@then(parsers.parse('the appointment of "{owner}" is still "{status}" at "{hhmm}"'))
def still(booking: Booking, owner: str, status: str, hhmm: str) -> None:
    record = AppointmentRecord.objects.get(id=booking.labels[owner].value)
    assert (record.status, record.start) == (status, _at(hhmm))


@given(parsers.parse('"{patient}" waits for a slot on Monday'))
def waits(booking: Booking, patient: str) -> None:
    WaitlistEntryRecord.objects.create(
        patient_id=booking.user(patient).id.value,
        appointment_type_id=booking.world.scene.kind.value,
        status="WAITING",
        earliest=_at("08:00", MONDAY),
        latest=_at("18:00", MONDAY),
        created_at=NOW,
    )


@then(parsers.parse('the waitlist entry of "{patient}" is offered the appointment of "{owner}"'))
def offered(booking: Booking, patient: str, owner: str) -> None:
    entry = WaitlistEntryRecord.objects.get(patient_id=booking.user(patient).id.value)
    assert (entry.status, entry.offered_appointment_id) == ("OFFERED", booking.labels[owner].value)


@then(parsers.parse('the "{clinician}" slot at "{hhmm}" is free again'))
def free_again(booking: Booking, clinician: str, hhmm: str) -> None:
    starts = free_starts(container(), booking.world.scene, booking.profile(clinician))
    assert _at(hhmm) in starts
