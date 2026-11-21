"""Steps of the pages and API through the fake wiring."""

import dataclasses
from typing import Any

from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.identity.domain.user import Role
from drlibre.scheduling.application.ports.outbound import AppointmentType
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_booking import (
    patient_user,
)
from tests.builders_web import fake_clinician
from tests.fakes.booking import InMemoryAppointments
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import (
    COOKIE,
    TYPE_NAME,
    Scene,
    clinician_named,
    csv,
    mine,
    open_session,
    page_text,
    typed_patient,
)


@given("the agenda names the clinicians, the type and the rooms")
def agenda_names(world: FakeWorld, scene: Scene) -> None:
    for name, clinician_id in scene.clinicians.items():
        world.agenda.clinicians[clinician_id] = clinician_named(name)
    world.agenda.labels[scene.type] = TYPE_NAME
    world.agenda.labels.update({room_id: name for name, room_id in scene.rooms.items()})


@given("the caller is a clinician")
def caller_is_clinician(world: FakeWorld, scene: Scene) -> None:
    scene.caller = Id()
    world.users.save(patient_user(scene.caller, email="dr@example.org", role=Role.CLINICIAN))


@when("the patient opens their appointments page")
def opens_appointments(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.get("/portal/appointments")
    assert scene.page.status_code == 200, scene.page.content


@given("the agenda no longer lists the appointment")
def agenda_drops(world: FakeWorld) -> None:
    world.agenda.appointments = InMemoryAppointments()


@when("the patient opens the move page of the appointment")
def opens_move_page(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.get(f"/portal/appointments/{mine(scene).id}/reschedule")


@then(parsers.parse("the page answers {status:d}"))
def page_answers(scene: Scene, status: int) -> None:
    assert scene.page.status_code == status, scene.page.content


@then(parsers.parse('the page offers "{actions}" for the appointment'))
def page_offers(scene: Scene, actions: str) -> None:
    body = page_text(scene)
    base = f"/portal/appointments/{mine(scene).id}"
    shown = {
        label
        for label, url in (("Déplacer", f"{base}/reschedule"), ("Annuler", f"{base}/cancel"))
        if f'href="{url}"' in body
    }
    assert shown == (set() if actions == "nothing" else set(csv(actions)))
    assert f'href="{base}.ics"' in body


@when(parsers.parse("the {who} posts '{body}' to {action} it"))
def posts_to_api(
    world: FakeWorld, scene: Scene, web: Client, who: str, body: str, action: str
) -> None:
    caller = scene.caller if who in ("caller", "clinician") else None
    if who == "admin":
        caller = scene.actor
    if who == "clinician" and caller is not None and caller not in world.users.rows:
        world.users.save(patient_user(caller, email="dr@example.org", role=Role.CLINICIAN))
    open_session(world, web, caller or scene.patient)
    url = f"/api/v1/appointments/{mine(scene).id}/{action}"
    scene.page = web.post(url, body, content_type="application/json")


@then(parsers.parse('the API answers 200 with the appointment "{status}"'))
def api_accepted(scene: Scene, status: str) -> None:
    assert scene.page.status_code == 200, scene.page.content
    body = scene.page.json()
    assert (body["id"], body["status"]) == (str(mine(scene).id), status)


@then(parsers.parse('the API refuses with {status:d} "{code}"'))
def api_refused(scene: Scene, status: int, code: str) -> None:
    assert scene.page.status_code == status, scene.page.content
    assert scene.page.json()["code"] == code


@then(parsers.parse('the API refusal names the rules "{names}"'))
def api_refused_rules(scene: Scene, names: str) -> None:
    assert scene.page.json()["details"]["rules"] == csv(names)


@then(parsers.parse('the API refusal names the field "{field}"'))
def api_refused_field(scene: Scene, field: str) -> None:
    assert field in [item["field"] for item in scene.page.json()["details"]["fields"]]


@given(parsers.parse('the public pages know the type and "{name}"'))
def public_pages_know(world: FakeWorld, scene: Scene, name: str) -> None:
    fake_clinician(
        world,
        user_id=Id(),
        profile_id=scene.clinicians[name],
        department_id=scene.department,
        time_zone="Europe/Paris",
        name=f"Dr {name}",
    )
    kind = build.appointment_type(scene.department)
    world.appointment_types.save(dataclasses.replace(kind, id=scene.type))
    world.scheduling_directory.types[scene.type] = AppointmentType(
        scene.type, scene.department, 30, 0, active=True, time_zone="Europe/Paris"
    )


@when(parsers.parse('the patient confirms "{name}" at "{start}" on the booking page'))
def confirms_on_page(world: FakeWorld, scene: Scene, web: Client, name: str, start: str) -> None:
    open_session(world, web, scene.patient)
    slot = {"type": str(scene.type), "clinician": str(scene.clinicians[name]), "start": start}
    choice = web.get("/booking/new", slot)
    assert choice.status_code == 200, choice.content
    follow_to_confirmation(world, scene, web, web.post("/booking/new", slot))


def follow_to_confirmation(world: FakeWorld, scene: Scene, web: Client, done: Any) -> None:
    scene.page = done
    if done.status_code == 302:
        scene.appointment = world.booking_appointments.get(
            Id.parse(done["Location"].split("/")[-1])
        )
        scene.page = web.get(done["Location"])


@given(
    parsers.parse('the visitor sent their details for "{name}" at "{start}" on the booking page')
)
@when(
    parsers.parse('the visitor sends their details for "{name}" at "{start}" on the booking page')
)
def visitor_sends_details(
    world: FakeWorld, scene: Scene, web: Client, name: str, start: str
) -> None:
    slot = {"type": str(scene.type), "clinician": str(scene.clinicians[name]), "start": start}
    details = {**scene.form, "accepted_terms": "on"}
    sent = web.post("/booking/new", {**slot, **details})
    assert sent.status_code == 302, sent.content
    scene.view = sent["Location"]


@when(parsers.parse('the visitor enters the code "{code}" on the code page'))
def visitor_enters_code_on_page(world: FakeWorld, scene: Scene, web: Client, code: str) -> None:
    scene.rows_before = len(world.booking_appointments.rows)
    follow_to_confirmation(world, scene, web, web.post(scene.view, {"code": code}))


@then(parsers.parse('the page refuses with {status:d}, a message and the free slot "{start}"'))
def page_refused_with_slots(scene: Scene, status: int, start: str) -> None:
    assert scene.page.status_code == status, scene.page.content
    body = page_text(scene)
    assert 'role="alert"' in body
    assert f"start={start}" in body


@then("the patient account is created and its session cookie is set")
def account_and_cookie(world: FakeWorld, scene: Scene) -> None:
    assert typed_patient(world, scene).role is Role.PATIENT
    assert scene.page.cookies[COOKIE].value
    assert len(world.booking_appointments.rows) == scene.rows_before


@when(parsers.parse('the visitor holds "{name}" at "{start}" through the API'))
def visitor_holds_through_api(
    world: FakeWorld, scene: Scene, web: Client, name: str, start: str
) -> None:
    form = scene.form
    body = {"type": str(scene.type), "clinician": str(scene.clinicians[name]), "start": start}
    scene.page = web.post(
        "/api/v1/booking/holds", {**body, **form}, content_type="application/json"
    )


@then("the API answers 201 with the hold and opens no session")
def api_hold(scene: Scene) -> None:
    assert scene.page.status_code == 201, scene.page.content
    assert set(scene.page.json()) == {"hold_id", "provider_id", "expires_at"}
    assert COOKIE not in scene.page.cookies
    scene.view = f"/api/v1/booking/holds/{scene.page.json()['hold_id']}/verify"


@when(parsers.parse('the visitor posts the code "{code}" through the API'))
def visitor_verifies_through_api(world: FakeWorld, scene: Scene, web: Client, code: str) -> None:
    scene.page = web.post(scene.view, {"code": code}, content_type="application/json")


@then(parsers.parse('the API answers 200 with the appointment "{status}" and opens the session'))
def api_verified(scene: Scene, status: str) -> None:
    assert scene.page.status_code == 200, scene.page.content
    assert scene.page.json()["appointment"]["status"] == status
    assert scene.page.cookies[COOKIE].value


@then(
    "the confirmation page shows the appointment, its calendar file and the patient's appointments"
)
def confirmation_page_shown(scene: Scene) -> None:
    assert scene.page.status_code == 200, scene.page.content
    body = page_text(scene)
    assert scene.appointment is not None
    assert "Rendez-vous réservé" in body
    assert f'href="/booking/appointments/{scene.appointment.id}.ics"' in body
    assert 'href="/portal/"' in body
