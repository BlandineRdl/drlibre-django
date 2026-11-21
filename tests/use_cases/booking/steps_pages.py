"""Steps of the pages and API through the fake wiring."""

from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import (
    patient_user,
)
from tests.fakes.booking import InMemoryAppointments
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import (
    TYPE_NAME,
    Scene,
    clinician_named,
    csv,
    mine,
    open_session,
    page_text,
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
