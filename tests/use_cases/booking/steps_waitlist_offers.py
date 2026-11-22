"""Steps of waitlist offers, acceptances and expiry."""

import dataclasses
import re
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, patient_user
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_waitlist import actor
from tests.use_cases.booking.support import VISIT_REASON, Scene, at, booked, mine, open_session

ME = "patient@example.org"
WINDOW = r'from "(?P<start>[^"]+)" to "(?P<end>[^"]+)"'


def person(scene: Scene, email: str) -> Id:
    return scene.patient if email == ME else scene.people[email]


def entry_of(world: FakeWorld, scene: Scene, email: str) -> WaitlistEntry:
    (entry,) = [e for e in world.waitlist.rows.values() if e.patient_id == person(scene, email)]
    return entry


def wait(
    world: FakeWorld,
    scene: Scene,
    email: str,
    start: str,
    end: str,
    joined: str,
    *,
    clinician: str | None = None,
    appointment_type: Id | None = None,
) -> WaitlistEntry:
    entry = WaitlistEntry.join(
        patient_id=person(scene, email),
        appointment_type_id=appointment_type or scene.type,
        clinician_id=scene.clinicians[clinician] if clinician else None,
        earliest=at(start),
        latest=at(end),
        at=at(joined),
    )
    world.waitlist.rows[entry.id] = entry
    return entry


def set_entry(world: FakeWorld, entry: WaitlistEntry, **changes: Any) -> None:
    world.waitlist.rows[entry.id] = dataclasses.replace(entry, **changes)


def cancelled_appointment(
    world: FakeWorld, scene: Scene, name: str, start: str, appointment_type: Id | None = None
) -> Appointment:
    appointment = existing_appointment(
        patient_id=Id(),
        clinician_id=scene.clinicians[name],
        appointment_type_id=appointment_type or scene.type,
        start=at(start),
        end=at(start) + timedelta(minutes=30),
        status=AppointmentStatus.CANCELLED,
        reason=VISIT_REASON,
    )
    world.booking_appointments.rows.append(appointment)
    scene.freed[start] = appointment
    return appointment


def attempt(world: FakeWorld, scene: Scene, call: Callable[[], object]) -> None:
    scene.waitlist_before = dict(world.waitlist.rows)
    scene.rows_before = len(world.booking_appointments.rows)
    try:
        result = call()
        if isinstance(result, Appointment):
            scene.appointment = result
    except DomainError as error:
        scene.error = error


@given(parsers.re(rf'"(?P<email>[^"]+)" waits {WINDOW} since "(?P<joined>[^"]+)"$'))
def waits(world: FakeWorld, scene: Scene, email: str, start: str, end: str, joined: str) -> None:
    wait(world, scene, email, start, end, joined)


@given(
    parsers.re(
        rf'"(?P<email>[^"]+)" waits preferring "(?P<name>[^"]+)" {WINDOW}'
        r' since "(?P<joined>[^"]+)"$'
    )
)
def waits_preferring(
    world: FakeWorld, scene: Scene, email: str, name: str, start: str, end: str, joined: str
) -> None:
    wait(world, scene, email, start, end, joined, clinician=name)


@given(
    parsers.re(rf'"(?P<email>[^"]+)" waits for another type {WINDOW} since "(?P<joined>[^"]+)"$')
)
def waits_other_type(
    world: FakeWorld, scene: Scene, email: str, start: str, end: str, joined: str
) -> None:
    wait(world, scene, email, start, end, joined, appointment_type=Id())


@given(
    parsers.re(
        rf'"(?P<email>[^"]+)" waits {WINDOW} already "(?P<status>[A-Z]+)"'
        r' since "(?P<joined>[^"]+)"$'
    )
)
def waits_with_status(
    world: FakeWorld, scene: Scene, email: str, start: str, end: str, status: str, joined: str
) -> None:
    entry = wait(world, scene, email, start, end, joined)
    set_entry(world, entry, status=WaitlistStatus(status))


@given(parsers.parse('the entry of "{email}" is "{status}"'))
def entry_status(world: FakeWorld, scene: Scene, email: str, status: str) -> None:
    set_entry(world, entry_of(world, scene, email), status=WaitlistStatus(status))


@given(parsers.parse('a cancelled appointment with "{name}" at "{start}"'))
def cancelled(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    cancelled_appointment(world, scene, name, start)


@given(parsers.parse('a cancelled appointment of another type with "{name}" at "{start}"'))
def cancelled_other_type(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    other = Id()
    cancelled_appointment(world, scene, name, start, appointment_type=other)
    world.free_slots.free.add((scene.clinicians[name], other, at(start)))


@given(parsers.parse('"{name}" is no longer free at "{start}"'))
def no_longer_free(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    world.free_slots.free.discard((scene.clinicians[name], scene.type, at(start)))


@given(parsers.parse('"{email}" holds the offer of the cancelled appointment at "{start}"'))
def holds_offer(world: FakeWorld, scene: Scene, email: str, start: str) -> None:
    entry = wait(world, scene, email, "2026-11-22 00:00", "2026-11-30 00:00", "2026-11-02 08:00")
    set_entry(world, entry.offered(scene.freed[start].id))


@given(
    parsers.re(
        r'"(?P<email>[^"]+)" is offered the cancelled appointment with "(?P<name>[^"]+)"'
        r' at "(?P<start>[^"]+)"(, waiting until "(?P<end>[^"]+)")?$'
    )
)
def offered(
    world: FakeWorld, scene: Scene, email: str, name: str, start: str, end: str | None
) -> None:
    freed = cancelled_appointment(world, scene, name, start)
    entry = wait(world, scene, email, "2026-11-19 00:00", end or "2026-11-30 00:00", "2026-11-01")
    set_entry(world, entry.offered(freed.id))


@when(parsers.parse('the admin offers a slot to the entry of "{email}"'))
@when(parsers.parse('the clinician offers a slot to the entry of "{email}"'))
def admin_offers(world: FakeWorld, scene: Scene, email: str) -> None:
    entry = entry_of(world, scene, email)
    attempt(
        world,
        scene,
        lambda: world.app.offer_cancelled_slot.execute(actor_id=actor(scene), entry_id=entry.id),
    )


def accept(world: FakeWorld, scene: Scene, by: Id, entry_id: Id) -> None:
    attempt(
        world,
        scene,
        lambda: world.app.accept_waitlist_offer.execute(actor_id=by, entry_id=entry_id),
    )


@when(parsers.parse('the patient accepts the offer of "{email}"'))
def patient_accepts(world: FakeWorld, scene: Scene, email: str) -> None:
    accept(world, scene, scene.patient, entry_of(world, scene, email).id)


@when(parsers.parse('the admin accepts the offer of "{email}"'))
@when(parsers.parse('the clinician accepts the offer of "{email}"'))
def staff_accepts(world: FakeWorld, scene: Scene, email: str) -> None:
    accept(world, scene, actor(scene), entry_of(world, scene, email).id)


@when("the patient accepts an unknown entry")
def accepts_unknown(world: FakeWorld, scene: Scene) -> None:
    accept(world, scene, scene.patient, Id())


@when(parsers.parse('another patient books "{name}" at "{start}"'))
def another_books(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    other = Id()
    world.users.save(patient_user(other, email="other@example.org"))
    scene.appointment = world.app.book_appointment.execute(
        patient_id=other,
        appointment_type_id=scene.type,
        clinician_id=scene.clinicians[name],
        start=at(start),
    )
    scene.caller = other


@then("the other patient's booking is placed")
def other_booked(scene: Scene) -> None:
    appointment = booked(scene)
    assert (appointment.status, appointment.patient_id) == (AppointmentStatus.BOOKED, scene.caller)


@then(parsers.parse('the offer is refused as "{code}"'))
def offer_refused(scene: Scene, code: str) -> None:
    assert scene.error is not None
    assert scene.error.code.value == code


def offered_to(world: FakeWorld, scene: Scene, email: str, appointment: Appointment) -> None:
    assert scene.error is None, scene.error
    entry = entry_of(world, scene, email)
    assert (entry.status, entry.offered_appointment_id) == (WaitlistStatus.OFFERED, appointment.id)
    offers = [e for e in world.waitlist.rows.values() if e.status is WaitlistStatus.OFFERED]
    assert [e.offered_appointment_id for e in offers].count(appointment.id) == 1


@then(parsers.parse('the entry of "{email}" is offered the appointment the patient cancelled'))
def offered_cancelled(world: FakeWorld, scene: Scene, email: str) -> None:
    offered_to(world, scene, email, mine(scene))


@then(parsers.parse('the entry of "{email}" is offered the cancelled appointment at "{start}"'))
def offered_freed(world: FakeWorld, scene: Scene, email: str, start: str) -> None:
    offered_to(world, scene, email, scene.freed[start])


@then("only the entry with the lowest id is offered the appointment the patient cancelled")
def lowest_id_offered(world: FakeWorld, scene: Scene) -> None:
    first, second = sorted(world.waitlist.rows.values(), key=lambda e: e.id.value)
    assert first.offered_appointment_id == mine(scene).id
    assert second.status is WaitlistStatus.WAITING


@then(
    parsers.parse('the appointment of "{email}" is with "{name}" at "{start}" for the offered type')
)
def placed_as_offered(world: FakeWorld, scene: Scene, email: str, name: str, start: str) -> None:
    appointment = booked(scene)
    freed = scene.freed[start]
    assert appointment.patient_id == person(scene, email)
    assert (appointment.clinician_id, appointment.start) == (scene.clinicians[name], at(start))
    assert appointment.appointment_type_id == freed.appointment_type_id
    assert world.booking_appointments.get(appointment.id) == appointment


@then(
    parsers.re(
        r'the entry of "(?P<email>[^"]+)" is now "(?P<status>[A-Z]+)"(?P<cleared> with no offer)?$'
    )
)
def entry_now(world: FakeWorld, scene: Scene, email: str, status: str, cleared: str | None) -> None:
    entry = entry_of(world, scene, email)
    assert entry.status is WaitlistStatus(status)
    if cleared:
        assert entry.offered_appointment_id is None


@then(parsers.parse('the entry of "{email}" is unchanged'))
def unchanged(world: FakeWorld, scene: Scene, email: str) -> None:
    entry = entry_of(world, scene, email)
    assert scene.waitlist_before[entry.id] == entry


@then("no entry was offered")
def nothing_offered(world: FakeWorld, scene: Scene) -> None:
    assert world.waitlist.rows == scene.waitlist_before
    assert "booking.waitlist_offered" not in world.audit.actions()
    assert "Créneau proposé" not in [n.title for n in world.notifications.rows]
    assert "Un créneau vous est proposé" not in [m.subject for m in world.outbox.queued]


@then(parsers.parse('the own list of "{email}" shows the offer at "{start}" that can be accepted'))
def own_offer(world: FakeWorld, scene: Scene, email: str, start: str) -> None:
    (row,) = world.app.waitlist_queries.own_entries(person(scene, email))
    assert row.offered_start == at(start)
    assert row.entry.acceptable_by_patient(at(start), world.clock.now())


@then(
    parsers.parse('"{email}" has one "{title}" notification at "{local}", linking no appointment')
)
def notified_without_link(
    world: FakeWorld, scene: Scene, email: str, title: str, local: str
) -> None:
    rows = [n for n in world.notifications.rows if n.recipient_id == person(scene, email)]
    assert [(n.title, n.appointment_id) for n in rows] == [(title, None)]
    assert local in rows[0].body


@then(parsers.parse('"{email}" has one "{title}" notification at "{local}" about the appointment'))
def notified_about(world: FakeWorld, scene: Scene, email: str, title: str, local: str) -> None:
    rows = [n for n in world.notifications.rows if n.recipient_id == person(scene, email)]
    assert [(n.title, n.appointment_id) for n in rows] == [(title, booked(scene).id)]
    assert local in rows[0].body


@then(
    parsers.parse(
        'one email "{subject}" to "{email}" names the time "{start}", hospital and provider'
        ' "{name}", without a reason, linking only to the sign-in page'
    )
)
def waitlist_email(
    world: FakeWorld, scene: Scene, subject: str, email: str, start: str, name: str
) -> None:
    (mail,) = [m for m in world.outbox.queued if m.to == (email,)]
    assert mail.subject == subject
    local = at(start).astimezone(ZoneInfo("Europe/Paris"))
    assert f"{local:%d/%m/%Y à %H:%M}" in mail.body
    assert "Hôpital Test" in mail.body
    assert name in mail.body
    assert VISIT_REASON not in mail.body
    assert "Empêchement" not in mail.body
    assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


def audited_ids_only(world: FakeWorld, by: Id | None, action: str) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert entry.actor == by
    assert entry.entity_type == "waitlist_entry"
    metadata = dict(entry.metadata)
    for key, value in metadata.items():
        if key.endswith("_id"):
            uuid.UUID(str(value))
        else:
            assert value in {*WaitlistStatus, "ONLINE", "STAFF"}, (key, value)


@then(
    parsers.parse(
        'the audit holds "{action}" by the signed-in patient, with ids and the source only'
    )
)
def audited_patient_source(world: FakeWorld, scene: Scene, action: str) -> None:
    audited_ids_only(world, scene.patient, action)


@then(parsers.parse('the audit holds "{action}" by the admin, with ids and the source only'))
def audited_admin_source(world: FakeWorld, scene: Scene, action: str) -> None:
    audited_ids_only(world, actor(scene), action)


@then(parsers.parse('the audit holds "{action}" by nobody with ids only'))
def audited_by_nobody(world: FakeWorld, action: str) -> None:
    audited_ids_only(world, None, action)


@when("the waitlist expiry job runs")
def expiry_runs(world: FakeWorld, scene: Scene) -> None:
    if not scene.expiry_runs:
        scene.waitlist_before = dict(world.waitlist.rows)
    scene.expiry_runs.append(world.app.expire_waitlist.execute())


@then(parsers.parse("the job changed {counts} entries"))
@then(parsers.parse("the job changed {counts} entries, then {later:d}"))
def job_changed(scene: Scene, counts: str, later: int | None = None) -> None:
    expected = [int(counts)] if later is None else [int(counts), later]
    assert scene.expiry_runs == expected


@then(parsers.parse('the audit holds "{action}" by nobody with the status "{status}"'))
def audited_status(world: FakeWorld, action: str, status: str) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert (entry.actor, entry.entity_type) == (None, "waitlist_entry")
    assert dict(entry.metadata) == {"status": status}


def caller_of(scene: Scene, who: str) -> Id | None:
    return {"patient": scene.patient, "visitor": None}.get(who, scene.actor)


def post_api(
    world: FakeWorld, scene: Scene, web: Client, caller: Id | None, url: str, body: dict[str, str]
) -> Any:
    scene.waitlist_before = dict(world.waitlist.rows)
    scene.rows_before = len(world.booking_appointments.rows)
    if caller is not None:
        open_session(world, web, caller)
    return web.post(f"/api/v1{url}", body, content_type="application/json")


@when(
    parsers.re(rf"the (?P<who>patient|visitor|clinician|admin) posts the waitlist join {WINDOW}$")
)
@when(parsers.re(rf'the (?P<who>admin) posts the waitlist join of "(?P<email>[^"]+)" {WINDOW}$'))
def posts_join(
    world: FakeWorld, scene: Scene, web: Client, who: str, start: str, end: str, email: str = ""
) -> None:
    body = {"appointment_type_id": str(scene.type), "from_date": start, "to_date": end}
    if email:
        body["patient_email"] = email
    scene.page = post_api(world, scene, web, caller_of(scene, who), "/waitlist", body)


@then(parsers.parse('the API answers 201 with a "{status}" entry for "{email}"'))
def api_entry(scene: Scene, status: str, email: str) -> None:
    assert scene.page.status_code == 201, scene.page.content
    body = scene.page.json()
    assert (body["patient"], body["status"]) == (str(person(scene, email).value), status)


@when(
    parsers.re(
        r"the (?P<who>patient|clinician|admin) posts the acceptance"
        r' of the offer of "(?P<email>[^"]+)"$'
    )
)
def posts_accept(world: FakeWorld, scene: Scene, web: Client, who: str, email: str) -> None:
    url = f"/waitlist/{entry_of(world, scene, email).id}/accept"
    scene.page = post_api(world, scene, web, caller_of(scene, who), url, {})
    if scene.page.status_code == 201:
        scene.appointment = world.booking_appointments.get(Id.parse(scene.page.json()["id"]))


@then(parsers.parse('the appointment keeps the id of the entry of "{email}"'))
def keeps_entry_id(world: FakeWorld, scene: Scene, email: str) -> None:
    assert booked(scene).id == entry_of(world, scene, email).id
