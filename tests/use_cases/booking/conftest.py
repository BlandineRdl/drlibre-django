import dataclasses
import inspect
import re
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.booking.application.ports.inbound import AgendaFilter, HoldCreated, VerifiedBooking
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.session import Session, hash_token
from drlibre.identity.domain.user import Role, User
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import (
    bookable_clinician,
    bookable_type,
    booking_venue,
    existing_appointment,
    patient_user,
)
from tests.fakes.booking import AgendaClinician, InMemoryAppointments
from tests.fakes.world import FakeWorld

NETWORK = "10.0.0.1"
VISITOR_FORM: dict[str, Any] = {
    "full_name": "Léa Martin",
    "birth_date": "1990-05-17",
    "email": "lea@example.org",
    "phone": "0601020304",
    "reason": "Douleur au genou",
    "accepted_terms": True,
}


class Scene:
    def __init__(self) -> None:
        self.department = Id()
        self.type = Id()
        self.patient = Id()
        self.clinicians: dict[str, Id] = {}
        self.rooms: dict[str, Id] = {}
        self.appointment: Appointment | None = None
        self.error: DomainError | None = None
        self.rows_before = 0
        self.form: dict[str, Any] = dict(VISITOR_FORM)
        self.hold: HoldCreated | None = None
        self.holds: list[HoldCreated] = []
        self.verified: VerifiedBooking | None = None
        self.successes = 0
        self.existing: User | None = None
        self.mine: Appointment | None = None
        self.caller: Id | None = None
        self.page: Any = None


@pytest.fixture
def scene() -> Scene:
    return Scene()


def at(raw: str) -> datetime:
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",")]


def amend_type(world: FakeWorld, scene: Scene, **changes: Any) -> None:
    types = world.booking_directory.types
    types[scene.type] = dataclasses.replace(types[scene.type], **changes)


def amend_clinician(world: FakeWorld, scene: Scene, name: str, **changes: Any) -> None:
    directory = world.booking_directory.clinicians
    clinician_id = scene.clinicians[name]
    directory[clinician_id] = dataclasses.replace(directory[clinician_id], **changes)


def add_clinician(
    world: FakeWorld, scene: Scene, name: str, default_room: str | None = None
) -> None:
    room = scene.rooms[default_room] if default_room else None
    clinician = bookable_clinician(scene.department, default_room_id=room)
    scene.clinicians[name] = clinician.id
    world.booking_directory.clinicians[clinician.id] = clinician
    world.booking_directory.venues[clinician.id] = booking_venue(name)


def book(world: FakeWorld, scene: Scene, clinician: str | None, start: str) -> None:
    scene.rows_before = len(world.booking_appointments.rows)
    try:
        scene.appointment = world.app.book_appointment.execute(
            patient_id=scene.patient,
            appointment_type_id=scene.type,
            clinician_id=scene.clinicians[clinician] if clinician else None,
            start=at(start),
        )
    except DomainError as error:
        scene.error = error


@given(
    parsers.parse(
        "a department with an online appointment type of {minutes:d} minutes needing a room"
    )
)
def department(world: FakeWorld, scene: Scene, minutes: int) -> None:
    kind = bookable_type(scene.department, duration_minutes=minutes)
    scene.type = kind.id
    world.booking_directory.types[kind.id] = kind


@given(parsers.parse('rooms "{names}" in that department'))
def rooms(world: FakeWorld, scene: Scene, names: str) -> None:
    scene.rooms = {name: Id() for name in csv(names)}
    world.booking_directory.department_rooms[scene.department] = tuple(scene.rooms.values())


@given(parsers.parse('an active clinician "{name}" with default room "{room}" in that department'))
def clinician_with_room(world: FakeWorld, scene: Scene, name: str, room: str) -> None:
    add_clinician(world, scene, name, room)


@given(parsers.parse('an active clinician "{name}" in that department'))
def clinician(world: FakeWorld, scene: Scene, name: str) -> None:
    add_clinician(world, scene, name)


@given("a signed-in patient")
def patient(world: FakeWorld, scene: Scene) -> None:
    world.users.save(patient_user(scene.patient))


@given(parsers.parse('"{first}" and "{second}" are free at "{start}"'))
def free_both(world: FakeWorld, scene: Scene, first: str, second: str, start: str) -> None:
    for name in (first, second):
        world.free_slots.free.add((scene.clinicians[name], scene.type, at(start)))


@given("the appointment type is inactive")
def inactive_type(world: FakeWorld, scene: Scene) -> None:
    amend_type(world, scene, active=False)


@given("the appointment type is not bookable online")
def offline_type(world: FakeWorld, scene: Scene) -> None:
    amend_type(world, scene, bookable_online=False)
    world.agenda.offline_types.add(scene.type)


@given("the appointment type needs no room")
def roomless_type(world: FakeWorld, scene: Scene) -> None:
    amend_type(world, scene, needs_room=False)


@given(parsers.parse('the clinician "{name}" is inactive'))
def inactive_clinician(world: FakeWorld, scene: Scene, name: str) -> None:
    amend_clinician(world, scene, name, active=False)


@given(parsers.parse('the clinician "{name}" is in another department'))
def clinician_elsewhere(world: FakeWorld, scene: Scene, name: str) -> None:
    amend_clinician(world, scene, name, department_id=Id())


@given(parsers.parse('the clinician "{name}" has weight 0'))
def weightless_clinician(world: FakeWorld, scene: Scene, name: str) -> None:
    amend_clinician(world, scene, name, weight=0)


@given(parsers.parse('"{name}" was assigned at "{when_}"'))
def assigned(world: FakeWorld, scene: Scene, name: str, when_: str) -> None:
    amend_clinician(world, scene, name, last_assigned_at=at(when_))


@given(parsers.parse('"{name}" has an active appointment from "{start}" to "{end}"'))
def clinician_busy(world: FakeWorld, scene: Scene, name: str, start: str, end: str) -> None:
    world.booking_appointments.rows.append(
        existing_appointment(
            patient_id=Id(), clinician_id=scene.clinicians[name], start=at(start), end=at(end)
        )
    )


@given(
    parsers.parse('the patient has an active appointment with "{name}" from "{start}" to "{end}"')
)
def patient_busy(world: FakeWorld, scene: Scene, name: str, start: str, end: str) -> None:
    world.booking_appointments.rows.append(
        existing_appointment(
            patient_id=scene.patient,
            clinician_id=scene.clinicians[name],
            start=at(start),
            end=at(end),
        )
    )


@given(parsers.parse("the patient has {count:d} open online bookings"))
def open_bookings(world: FakeWorld, scene: Scene, count: int) -> None:
    for day in range(count):
        start = at("2026-11-24 09:00") + timedelta(days=day)
        world.booking_appointments.rows.append(
            existing_appointment(
                patient_id=scene.patient,
                clinician_id=scene.clinicians["B"],
                start=start,
                end=start + timedelta(minutes=30),
                source=Source.ROUND_ROBIN if day % 2 else Source.ONLINE,
            )
        )


@given(parsers.parse('the room "{room}" is used by someone else from "{start}" to "{end}"'))
def room_busy(world: FakeWorld, scene: Scene, room: str, start: str, end: str) -> None:
    world.booking_appointments.rows.append(
        existing_appointment(
            patient_id=Id(),
            clinician_id=Id(),
            start=at(start),
            end=at(end),
            room_id=scene.rooms[room],
            status=AppointmentStatus.CHECKED_IN,
        )
    )


@when(parsers.parse('the patient books "{name}" at "{start}"'))
def books_named(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    book(world, scene, name, start)


@when(parsers.parse('the patient books without naming a clinician at "{start}"'))
def books_first_available(world: FakeWorld, scene: Scene, start: str) -> None:
    book(world, scene, None, start)


@then(parsers.parse('the booking is refused as "{code}"'))
def refused(scene: Scene, code: str) -> None:
    assert scene.error is not None
    assert scene.error.code.value == code


@then(parsers.parse('the refusal names the resources "{names}"'))
def refused_resources(scene: Scene, names: str) -> None:
    assert scene.error is not None
    assert scene.error.details["resources"] == csv(names)


@then(parsers.parse('the refusal names the rules "{names}"'))
def refused_rules(scene: Scene, names: str) -> None:
    assert scene.error is not None
    assert scene.error.details["rules"] == csv(names)


@then("nothing was written")
def nothing_written(world: FakeWorld, scene: Scene) -> None:
    assert len(world.booking_appointments.rows) == scene.rows_before
    assert "booking.appointment_booked" not in world.audit.actions()
    assert world.booking_slot_refresh.refreshed == []
    assert world.outbox.queued == []
    assert world.ledger.assigned == {}


def booked(scene: Scene) -> Appointment:
    assert scene.appointment is not None, scene.error
    return scene.appointment


@then(parsers.parse('the appointment is "{status}" in room "{room}"'))
def booked_in_room(scene: Scene, status: str, room: str) -> None:
    assert booked(scene).status.value == status
    assert booked(scene).room_id == scene.rooms[room]


@then(parsers.parse('the appointment is "{status}" in no room'))
def booked_without_room(scene: Scene, status: str) -> None:
    assert booked(scene).status.value == status
    assert booked(scene).room_id is None


@then(parsers.parse('the appointment is "{status}" for "{source}"'))
def booked_for_source(scene: Scene, status: str, source: str) -> None:
    assert booked(scene).status.value == status
    assert booked(scene).source.value == source


@then(parsers.parse('the appointment is with "{name}"'))
def booked_with(scene: Scene, name: str) -> None:
    assert booked(scene).clinician_id == scene.clinicians[name]


@then("the appointment belongs to the signed-in patient")
def booked_for_patient(scene: Scene) -> None:
    assert booked(scene).patient_id == scene.patient


@then(parsers.parse("the appointment ends {minutes:d} minutes after it starts"))
def ends_after(scene: Scene, minutes: int) -> None:
    assert booked(scene).end - booked(scene).start == timedelta(minutes=minutes)


@then(parsers.parse('the last assignment of "{name}" is "{when_}"'))
def last_assignment(world: FakeWorld, scene: Scene, name: str, when_: str) -> None:
    assert world.ledger.assigned == {scene.clinicians[name]: at(when_)}


@then(parsers.parse('the audit holds "{action}"'))
def audited(world: FakeWorld, action: str) -> None:
    assert action in world.audit.actions()


@then(parsers.parse('the slots of "{name}" were refreshed'))
def refreshed(world: FakeWorld, scene: Scene, name: str) -> None:
    assert world.booking_slot_refresh.refreshed == [scene.clinicians[name]]


@then("a confirmation was queued")
def confirmation_queued(world: FakeWorld, scene: Scene) -> None:
    assert [m.to for m in world.outbox.queued] == [("patient@example.org",)]


@then("the booking offers no way to name an end time")
def no_end_time() -> None:
    assert "end" not in inspect.signature(FakeWorld().app.book_appointment.execute).parameters


@then("the booking offers no way to name a patient or a room")
def no_other_patient_or_room() -> None:
    names = set(inspect.signature(FakeWorld().app.book_appointment.execute).parameters)
    assert names == {"patient_id", "appointment_type_id", "clinician_id", "start"}


# --- visitor holds and codes -------------------------------------------------


def attempt[T](scene: Scene, call: Callable[[], T]) -> T | None:
    try:
        return call()
    except DomainError as error:
        scene.error = error
        return None


def hold_slot(
    world: FakeWorld,
    scene: Scene,
    clinician: str | None,
    start: str | datetime,
    *,
    email: str | None = None,
    network: str = NETWORK,
) -> HoldCreated | None:
    form: dict[str, Any] = {**scene.form, **({"email": email} if email else {})}
    moment = start if isinstance(start, datetime) else at(start)
    created = attempt(
        scene,
        lambda: world.app.create_hold.execute(
            appointment_type_id=scene.type,
            clinician_id=scene.clinicians[clinician] if clinician else None,
            start=moment,
            network=network,
            **form,
        ),
    )
    if created is not None:
        scene.hold = created
    return created


def verify_code(world: FakeWorld, scene: Scene, code: str) -> None:
    assert scene.hold is not None
    scene.rows_before = len(world.booking_appointments.rows)
    scene.verified = attempt(
        scene,
        lambda: world.app.verify_hold.execute(
            hold_id=scene.hold.hold_id, code=code, user_agent="pytest"
        ),
    )
    if scene.verified is not None:
        outcome = scene.verified.outcome
        scene.appointment = None if isinstance(outcome, DomainError) else outcome


def request_code(world: FakeWorld, scene: Scene, hold: HoldCreated, network: str = NETWORK) -> bool:
    before = scene.error
    scene.error = None
    attempt(scene, lambda: world.app.resend_code.execute(hold_id=hold.hold_id, network=network))
    refused = scene.error is not None
    scene.error = scene.error or before
    return not refused


def successive(start: str, index: int) -> datetime:
    return at(start) + timedelta(minutes=30 * index)


@given(parsers.parse('the visitor types {field} "{value}"'))
def visitor_types(scene: Scene, field: str, value: str) -> None:
    scene.form[field] = value


@given("the visitor leaves the phone and the reason empty")
def visitor_leaves_optionals(scene: Scene) -> None:
    scene.form.update(phone="", reason="")


@given("the visitor does not accept the terms")
def visitor_refuses_terms(scene: Scene) -> None:
    scene.form["accepted_terms"] = False


@given(parsers.parse('"{name}" is free every 30 minutes from "{start}" for {count:d} slots'))
def free_run(world: FakeWorld, scene: Scene, name: str, start: str, count: int) -> None:
    for index in range(count):
        world.free_slots.free.add((scene.clinicians[name], scene.type, successive(start, index)))


@given(parsers.parse('the clock is "{when_}"'))
def clock_is(world: FakeWorld, when_: str) -> None:
    world.clock.at = at(when_)


@given(parsers.parse('the sent code is "{code}"'))
def sent_code(world: FakeWorld, code: str) -> None:
    world.issuer.code = code


@given(parsers.parse('an active patient with email "{email}" and {password} password'))
def existing_patient(world: FakeWorld, scene: Scene, email: str, password: str) -> None:
    hashed = "hashed" if password == "a" else None
    scene.existing = patient_user(scene.patient, email=email, password_hash=hashed)
    world.users.save(scene.existing)


@given(parsers.parse('a user with role "{role}", {state}, and email "{email}"'))
def staff_user(world: FakeWorld, scene: Scene, state: str, role: str, email: str) -> None:
    scene.existing = patient_user(
        scene.patient, email=email, role=Role(role), active=state == "active"
    )
    world.users.save(scene.existing)


@given(parsers.parse('{count:d} holds were made from separate networks from "{start}" on "{name}"'))
def holds_from_separate_networks(
    world: FakeWorld, scene: Scene, count: int, start: str, name: str
) -> None:
    scene.holds = []
    for index in range(count):
        created = hold_slot(
            world,
            scene,
            name,
            successive(start, index),
            email=f"visitor{index}@example.org",
            network=f"10.1.0.{index}",
        )
        assert created is not None, scene.error
        scene.holds.append(created)


@given(parsers.parse('the visitor asks to hold "{name}" at "{start}"'))
@when(parsers.parse('the visitor asks to hold "{name}" at "{start}"'))
def visitor_holds(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    hold_slot(world, scene, name, start)


@given(parsers.parse('the visitor asks to hold the first available at "{start}"'))
@when(parsers.parse('the visitor asks to hold the first available at "{start}"'))
def visitor_holds_first_available(world: FakeWorld, scene: Scene, start: str) -> None:
    hold_slot(world, scene, None, start)


@when(parsers.parse('"{email}" asks to hold "{name}" at "{start}"'))
def other_visitor_holds(world: FakeWorld, scene: Scene, email: str, name: str, start: str) -> None:
    hold_slot(world, scene, name, start, email=email)


@when(parsers.parse('the visitor asks to hold "{name}" at "{start}" {count:d} times'))
def visitor_holds_repeatedly(
    world: FakeWorld, scene: Scene, name: str, start: str, count: int
) -> None:
    scene.successes = sum(hold_slot(world, scene, name, start) is not None for _ in range(count))


@when(
    parsers.parse(
        '{count:d} visitors on network "{network}" ask to hold "{name}" from "{start}" on'
    )
)
def visitors_hold_from_one_network(
    world: FakeWorld, scene: Scene, count: int, network: str, name: str, start: str
) -> None:
    scene.successes = 0
    for index in range(count):
        created = hold_slot(
            world,
            scene,
            name,
            successive(start, index),
            email=f"visitor{index}@example.org",
            network=network,
        )
        scene.successes += created is not None


@when(parsers.parse('a new code is asked for each of them from network "{network}"'))
def codes_from_one_network(world: FakeWorld, scene: Scene, network: str) -> None:
    scene.successes = sum(request_code(world, scene, hold, network) for hold in scene.holds)


@when(parsers.parse('the visitor enters the code "{code}"'))
def visitor_enters_code(world: FakeWorld, scene: Scene, code: str) -> None:
    verify_code(world, scene, code)


@when(parsers.parse("the visitor enters a wrong code {count:d} times"))
def visitor_enters_wrong_codes(world: FakeWorld, scene: Scene, count: int) -> None:
    for _ in range(count):
        verify_code(world, scene, "000000")


@when("the visitor asks for a new code")
def visitor_asks_new_code(world: FakeWorld, scene: Scene) -> None:
    assert scene.hold is not None
    request_code(world, scene, scene.hold)


@when(parsers.parse("the visitor asks for a new code {count:d} times"))
def visitor_asks_new_codes(world: FakeWorld, scene: Scene, count: int) -> None:
    assert scene.hold is not None
    scene.error = None
    scene.successes = sum(request_code(world, scene, scene.hold) for _ in range(count))


@given(parsers.parse("{minutes:d} minutes pass"))
@when(parsers.parse("{minutes:d} minutes pass"))
def minutes_pass(world: FakeWorld, minutes: int) -> None:
    world.clock.at += timedelta(minutes=minutes)


@when("the expiry job runs")
def expiry_job_runs(world: FakeWorld) -> None:
    world.app.expire_holds.execute()


@then(parsers.parse('the hold expires at "{when_}"'))
def hold_expires(scene: Scene, when_: str) -> None:
    assert scene.hold is not None
    assert scene.hold.expires_at == at(when_)


@then(parsers.parse('the slot of "{name}" at "{start}" is no longer offered'))
def slot_hidden(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    assert not world.free_slots.is_free(
        scene.clinicians[name], scene.type, at(start), ignoring_hold=None
    )


@then(parsers.parse('the slot of "{name}" at "{start}" is offered again'))
def slot_offered(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    assert world.free_slots.is_free(
        scene.clinicians[name], scene.type, at(start), ignoring_hold=None
    )


@then(parsers.parse('the hold is on "{name}"'))
def hold_on(scene: Scene, name: str) -> None:
    assert scene.hold is not None
    assert scene.hold.clinician_id == scene.clinicians[name]


def code_emails(world: FakeWorld) -> list[Any]:
    return [m for m in world.outbox.queued if m.subject == "Votre code de vérification"]


def confirmation_emails(world: FakeWorld) -> list[Any]:
    return [m for m in world.outbox.queued if m.subject == "Confirmation de votre rendez-vous"]


@then(parsers.parse('a 6 digit code was emailed to "{email}"'))
def code_emailed(world: FakeWorld, email: str) -> None:
    sent = code_emails(world)
    assert [m.to for m in sent] == [(email,)]
    assert re.search(r"\b\d{6}\b", sent[0].body)


@then(parsers.parse("{count:d} code emails were sent in all"))
def code_emails_sent(world: FakeWorld, count: int) -> None:
    assert len(code_emails(world)) == count


@then("the hold is gone")
def hold_gone(world: FakeWorld) -> None:
    assert world.holds.rows == {}
    assert world.codes.rows == {}


@then("the hold is still there")
def hold_kept(world: FakeWorld) -> None:
    assert len(world.holds.rows) == 1


@then("only the second hold and its code remain")
def only_second_hold(world: FakeWorld, scene: Scene) -> None:
    assert scene.hold is not None
    assert set(world.holds.rows) == {scene.hold.hold_id}
    assert set(world.codes.rows) == {scene.hold.hold_id}


@then(parsers.parse('the refusal names the field "{field}"'))
def refused_field(scene: Scene, field: str) -> None:
    assert scene.error is not None
    assert field in [item["field"] for item in scene.error.details["fields"]]


@then("no hold was created")
def no_hold(world: FakeWorld) -> None:
    assert world.holds.rows == {}
    assert world.outbox.queued == []


@then(parsers.parse('the first {count:d} requests succeeded and the next was refused as "{code}"'))
def limit_hit(scene: Scene, count: int, code: str) -> None:
    assert scene.successes == count
    assert scene.error is not None
    assert scene.error.details["rules"] == [code]


@then("no appointment and no account exist")
def nothing_created(world: FakeWorld, scene: Scene) -> None:
    assert world.booking_appointments.rows == []
    assert [u for u in world.users.rows.values() if u.email.value == scene.form["email"]] == []
    assert world.sessions.rows == {}


def verified(scene: Scene) -> VerifiedBooking:
    assert scene.verified is not None, scene.error
    return scene.verified


def typed_patient(world: FakeWorld, scene: Scene) -> User:
    found = [u for u in world.users.rows.values() if u.email.value == scene.form["email"]]
    assert len(found) == 1
    return found[0]


@then("a patient without password was created from the typed details with a verified email")
def passwordless_patient_created(world: FakeWorld, scene: Scene) -> None:
    patient = typed_patient(world, scene)
    assert patient.role is Role.PATIENT
    assert not patient.has_password
    assert patient.full_name == scene.form["full_name"]
    assert patient.birth_date == date.fromisoformat(scene.form["birth_date"])
    assert patient.phone == scene.form["phone"]
    assert patient.email_verified_at == world.clock.now()
    assert booked(scene).patient_id == patient.id


@then("a session of 24 hours that is never extended was opened for the patient")
def session_opened(world: FakeWorld, scene: Scene) -> None:
    opened = verified(scene)
    stored = world.sessions.by_token_hash(hash_token(opened.token))
    assert stored is not None
    assert stored.user_id == typed_patient(world, scene).id
    assert stored.expires_at == world.clock.now() + timedelta(hours=24)
    assert not stored.extendable
    assert not stored.needs_extension(at=world.clock.now() + timedelta(hours=23))


@then("the appointment belongs to the existing patient")
def booked_for_existing(scene: Scene) -> None:
    assert booked(scene).patient_id == scene.patient


@then("the profile of the existing patient is unchanged")
def profile_unchanged(world: FakeWorld, scene: Scene) -> None:
    stored = world.users.rows[scene.patient]
    assert dataclasses.replace(stored, last_login_at=None) == scene.existing
    assert len(world.users.rows) == 1


@then("the booking is refused with a message that does not say why")
def generic_refusal(scene: Scene) -> None:
    assert scene.error is not None
    assert scene.error.code.value == "forbidden"
    assert scene.error.message == "Cette réservation ne peut pas être effectuée."
    assert scene.error.details == {}


@then("the hold is released and nothing was created")
def released_and_nothing_created(world: FakeWorld, scene: Scene) -> None:
    assert world.holds.rows == {}
    assert world.codes.rows == {}
    assert world.booking_appointments.rows == []
    assert list(world.users.rows) == [scene.patient]
    assert world.sessions.rows == {}


@then("the answer carries nothing about any patient or appointment")
def answer_without_patient_data(scene: Scene) -> None:
    assert scene.hold is not None
    assert {f.name for f in dataclasses.fields(scene.hold)} == {
        "hold_id",
        "clinician_id",
        "expires_at",
    }


@then("both holds were answered and both codes emailed the same way")
def same_answers(world: FakeWorld) -> None:
    first, second = code_emails(world)
    assert (first.subject, first.body) == (second.subject, second.body)
    assert len(world.holds.rows) == 2


@then(parsers.parse('the booking failed as "{code}" while the patient session stays open'))
def failed_after_code(world: FakeWorld, scene: Scene, code: str) -> None:
    result = verified(scene)
    assert isinstance(result.outcome, DomainError)
    assert result.outcome.code.value == code
    assert world.sessions.by_token_hash(hash_token(result.token)) is not None
    assert typed_patient(world, scene).role is Role.PATIENT
    assert world.holds.rows == {}
    assert len(world.booking_appointments.rows) == scene.rows_before


@then("the confirmation names the time, hospital and provider and links to the sign-in page only")
def confirmation_content(scene: Scene, world: FakeWorld) -> None:
    (mail,) = confirmation_emails(world)
    assert mail.to == (scene.form["email"],)
    assert "23/11/2026 à 10:00" in mail.body
    assert "Hôpital Test" in mail.body
    assert "A" in mail.body
    assert "http://localhost:8000/sign-in" in mail.body
    assert scene.form["reason"] not in mail.body
    assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


@then("the code email carries no link")
def code_email_without_link(world: FakeWorld) -> None:
    assert all("http" not in m.body for m in code_emails(world))


@then("exactly one confirmation email was sent")
def one_confirmation(world: FakeWorld) -> None:
    assert len(confirmation_emails(world)) == 1


@then(parsers.parse('the audit entry "{action}" has no actor and only the email domain'))
def audit_anonymous(world: FakeWorld, action: str) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert entries
    for entry in entries:
        assert entry.actor is None
        assert dict(entry.metadata)["email_domain"] == "example.org"


@then(parsers.parse('the audit entry "{action}" names the reason "{reason}"'))
def audit_reason(world: FakeWorld, action: str, reason: str) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert [dict(e.metadata)["reason"] for e in entries] == [reason]


@then(
    parsers.parse('the audit entry "{action}" has the patient as actor and only the email domain')
)
def audit_by_patient(world: FakeWorld, scene: Scene, action: str) -> None:
    patient = typed_patient(world, scene)
    entries = [e for e in world.audit.entries if e.action == action]
    assert entries
    for entry in entries:
        assert entry.actor == patient.id
        assert dict(entry.metadata)["email_domain"] == "example.org"


@then("no audit entry holds personal data")
def audit_without_personal_data(world: FakeWorld, scene: Scene) -> None:
    personal = (scene.form["email"], scene.form["full_name"], scene.form["phone"])
    text = " ".join(f"{e.metadata}" for e in world.audit.entries)
    assert not any(item in text for item in personal)


@then(parsers.parse('the audit holds {count:d} "{action}" entries'))
def audit_count(world: FakeWorld, count: int, action: str) -> None:
    assert world.audit.actions().count(action) == count


@then("no round robin assignment was recorded")
def nobody_assigned(world: FakeWorld) -> None:
    assert world.ledger.assigned == {}


@then(parsers.parse('{count:d} period of "{name}" is held on "2026-11-23"'))
def held_periods(world: FakeWorld, scene: Scene, count: int, name: str) -> None:
    periods = world.app.open_holds.execute(
        clinician_ids=(scene.clinicians[name],),
        start=at("2026-11-23 00:00"),
        end=at("2026-11-24 00:00"),
        at=world.clock.now(),
    )
    assert len(periods) == count
    assert all(p.start == at("2026-11-23 09:00") for p in periods)


# --- patient cancels or moves ------------------------------------------------

VISIT_REASON = "Douleur au genou droit"


def mine(scene: Scene) -> Appointment:
    assert scene.mine is not None
    return scene.mine


def change(world: FakeWorld, scene: Scene, call: Callable[[], Appointment]) -> None:
    try:
        scene.appointment = call()
    except DomainError as error:
        scene.error = error


@given(
    parsers.parse(
        'the patient has a "{status}" appointment with "{name}" at "{start}" in room "{room}"'
    )
)
def my_appointment(
    world: FakeWorld, scene: Scene, status: str, name: str, start: str, room: str
) -> None:
    scene.mine = existing_appointment(
        patient_id=scene.patient,
        clinician_id=scene.clinicians[name],
        appointment_type_id=scene.type,
        start=at(start),
        end=at(start) + timedelta(minutes=30),
        room_id=scene.rooms[room],
        status=AppointmentStatus(status),
        reason=VISIT_REASON,
    )
    world.booking_appointments.rows.append(scene.mine)


@given("the appointment belongs to another patient")
def someone_elses(world: FakeWorld, scene: Scene) -> None:
    rows = world.booking_appointments.rows
    other = dataclasses.replace(mine(scene), patient_id=Id())
    rows[rows.index(mine(scene))] = other
    scene.mine = other


@given(parsers.parse('"{name}" is free at "{start}"'))
def free_one(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    world.free_slots.free.add((scene.clinicians[name], scene.type, at(start)))


@given(parsers.parse('"{name}" is free at "{start}" once the appointment is ignored'))
def free_behind(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    world.free_slots.behind[(scene.clinicians[name], scene.type, at(start))] = mine(scene).id


@given("the appointment type is bookable online")
def online_type() -> None:
    """The background type is already bookable online."""


@given(parsers.parse('the rooms "{names}" are used by someone else from "{start}" to "{end}"'))
def rooms_busy(world: FakeWorld, scene: Scene, names: str, start: str, end: str) -> None:
    for room in csv(names):
        room_busy(world, scene, room, start, end)


@when("the patient cancels it without a reason")
def cancels_without_reason(world: FakeWorld, scene: Scene) -> None:
    cancels(world, scene, "   ")


@when(parsers.parse('the patient cancels it giving the reason "{reason}"'))
def cancels(world: FakeWorld, scene: Scene, reason: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.cancel_appointment.execute(
            appointment_id=mine(scene).id, patient_id=scene.patient, reason=reason
        ),
    )


@when(parsers.parse("the patient cancels it giving a reason of {length:d} characters"))
def cancels_at_length(world: FakeWorld, scene: Scene, length: int) -> None:
    cancels(world, scene, "x" * length)


@when("the patient cancels an unknown appointment")
def cancels_unknown(world: FakeWorld, scene: Scene) -> None:
    change(
        world,
        scene,
        lambda: world.app.cancel_appointment.execute(
            appointment_id=Id(), patient_id=scene.patient, reason="Empêchement"
        ),
    )


@when(parsers.parse('the patient moves it to "{start}"'))
def moves(world: FakeWorld, scene: Scene, start: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.reschedule_appointment.execute(
            appointment_id=mine(scene).id, patient_id=scene.patient, start=at(start)
        ),
    )


@when(parsers.parse('the patient moves an unknown appointment to "{start}"'))
def moves_unknown(world: FakeWorld, scene: Scene, start: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.reschedule_appointment.execute(
            appointment_id=Id(), patient_id=scene.patient, start=at(start)
        ),
    )


@then(parsers.parse('the refusal names the status "{status}"'))
def refused_status(scene: Scene, status: str) -> None:
    assert scene.error is not None
    assert scene.error.details == {"status": status}


@then("nothing was changed or notified")
def nothing_changed(world: FakeWorld, scene: Scene) -> None:
    assert world.booking_appointments.get(mine(scene).id) == mine(scene)
    assert world.notifications.rows == []
    assert world.outbox.queued == []
    assert world.booking_slot_refresh.refreshed == []
    changes = {"booking.appointment_cancelled", "booking.appointment_rescheduled"}
    assert not changes & set(world.audit.actions())


@then(parsers.parse('the patient is offered "{actions}"'))
def offered(world: FakeWorld, scene: Scene, actions: str) -> None:
    listed = world.app.list_patient_appointments.execute(
        patient_id=scene.patient, agenda_filter=AgendaFilter()
    )
    (entry,) = [e for e in listed.upcoming + listed.past if e.appointment.id == mine(scene).id]
    allowed = entry.allowed_actions
    expected = set() if actions == "nothing" else set(csv(actions))
    assert {action.value for action in allowed} == expected


@then(parsers.parse('the appointment is cancelled now for the reason "{reason}"'))
def cancelled_now(world: FakeWorld, scene: Scene, reason: str) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None
    assert stored.status is AppointmentStatus.CANCELLED
    assert stored.cancelled_at == world.clock.now()
    assert stored.cancellation_reason == reason


@then("the appointment has left the upcoming appointments for the past ones")
def joined_past(world: FakeWorld, scene: Scene) -> None:
    listed = world.app.list_patient_appointments.execute(
        patient_id=scene.patient, agenda_filter=AgendaFilter()
    )
    assert mine(scene).id in [e.appointment.id for e in listed.past]
    assert mine(scene).id not in [e.appointment.id for e in listed.upcoming]


@then(
    parsers.parse(
        'the appointment is "{status}" from "{start}" for {minutes:d} minutes in room "{room}"'
    )
)
def moved_to(
    world: FakeWorld, scene: Scene, status: str, start: str, minutes: int, room: str
) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None, scene.error
    assert stored.status.value == status
    assert (stored.start, stored.end) == (at(start), at(start) + timedelta(minutes=minutes))
    assert stored.room_id == scene.rooms[room]
    assert world.booking_slot_refresh.refreshed == [stored.clinician_id]


@then("the move offers no way to name an end time")
def move_without_end() -> None:
    names = set(inspect.signature(FakeWorld().app.reschedule_appointment.execute).parameters)
    assert names == {"appointment_id", "patient_id", "start"}


@then(parsers.parse('the patient has one "{title}" notification about the appointment'))
def notified(world: FakeWorld, scene: Scene, title: str) -> None:
    rows = [n for n in world.notifications.rows if n.recipient_id == scene.patient]
    assert [(n.title, n.appointment_id) for n in rows] == [(title, mine(scene).id)]


@then(
    parsers.parse('the patient has one "{title}" notification about the appointment at "{when_}"')
)
def notified_at(world: FakeWorld, scene: Scene, title: str, when_: str) -> None:
    notified(world, scene, title)
    assert when_ in world.notifications.rows[0].body


@then(
    parsers.parse(
        'one email "{subject}" names the time, hospital and provider, without the reason,'
        " linking only to the sign-in page"
    )
)
def change_email(world: FakeWorld, scene: Scene, subject: str) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None
    (mail,) = world.outbox.queued
    assert (mail.subject, mail.to) == (subject, ("patient@example.org",))
    local = stored.start.astimezone(ZoneInfo("Europe/Paris"))
    assert f"{local:%d/%m/%Y à %H:%M}" in mail.body
    assert "Hôpital Test" in mail.body
    assert "A" in mail.body
    assert VISIT_REASON not in mail.body
    assert stored.cancellation_reason is None or stored.cancellation_reason not in mail.body
    assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


def change_entry(world: FakeWorld, scene: Scene, action: str) -> dict[str, object]:
    entries = [e for e in world.audit.entries if e.action == action]
    assert [e.actor for e in entries] == [scene.patient]
    return dict(entries[0].metadata)


@then(parsers.parse('the audit entry "{action}" has the patient as actor and holds no reason'))
def audit_without_reason(world: FakeWorld, scene: Scene, action: str) -> None:
    metadata = change_entry(world, scene, action)
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None
    assert stored.cancellation_reason
    assert stored.cancellation_reason not in f"{metadata}"


@then(
    parsers.parse('the audit entry "{action}" has the patient as actor and holds no personal data')
)
def audit_ids_only(world: FakeWorld, scene: Scene, action: str) -> None:
    metadata = change_entry(world, scene, action)
    assert metadata == {
        "clinician_id": str(scene.clinicians["A"]),
        "room_id": str(scene.rooms["R2"]),
    }


# --- reminders ----------------------------------------------------------------


@given("the reminder job ran")
@when("the reminder job runs")
def reminder_job_runs(world: FakeWorld) -> None:
    world.app.send_reminders.execute()


@when("the reminder job runs twice")
def reminder_job_runs_twice(world: FakeWorld) -> None:
    reminder_job_runs(world)
    reminder_job_runs(world)


def reminder_emails(world: FakeWorld) -> list[Any]:
    return [m for m in world.outbox.queued if m.subject == "Rappel de votre rendez-vous"]


@then(parsers.parse('the patient has "{title}" notifications for the appointments at "{starts}"'))
def reminded_for(world: FakeWorld, scene: Scene, title: str, starts: str) -> None:
    by_id = {a.id: a.start for a in world.booking_appointments.rows}
    rows = [n for n in world.notifications.rows if n.recipient_id == scene.patient]
    assert all(n.title == title for n in rows)
    assert sorted(by_id[n.appointment_id] for n in rows if n.appointment_id) == [
        at(start) for start in csv(starts)
    ]


@then(parsers.parse("{count:d} reminder emails were sent"))
def reminder_emails_sent(world: FakeWorld, count: int) -> None:
    assert len(reminder_emails(world)) == count


@then(
    "each reminder email names the time, hospital and provider, without the reason,"
    " linking only to the sign-in page"
)
def reminder_content(world: FakeWorld) -> None:
    sent = reminder_emails(world)
    assert [m.to for m in sent] == [("patient@example.org",)] * 2
    for mail, local in zip(sent, ("20/11/2026 à 13:00", "21/11/2026 à 11:00"), strict=True):
        assert local in mail.body
        assert VISIT_REASON not in mail.body
        assert "Hôpital Test" in mail.body
        assert "A" in mail.body
        assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


@then(parsers.parse('the audit entry "{action}" has no actor and counts {count:d}'))
def audit_counted(world: FakeWorld, action: str, count: int) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert entry.actor is None
    assert dict(entry.metadata) == {"count": count}


# --- pages and API through the fake wiring -----------------------------------

COOKIE = settings.SESSION_COOKIE_NAME
TYPE_NAME = "Consultation de suivi"


def clinician_named(name: str) -> AgendaClinician:
    return AgendaClinician(
        name=f"Claire {name}",
        title="Dr",
        specialty="Cardiologie",
        hospital_name="Hôpital du Lamentin",
        hospital_address="1 rue des Alizés, 97232 Le Lamentin",
        time_zone="America/Martinique",
        department="Rythmologie",
    )


@pytest.fixture
def web(world: FakeWorld) -> Iterator[Client]:
    """A browser stand-in served by the real pages and API over the fake wiring."""
    use_container(world.app)
    yield Client()
    use_container(None)


def open_session(world: FakeWorld, web: Client, user_id: Id) -> None:
    token = f"token-{user_id}"
    user = world.users.rows[user_id]
    world.sessions.add(
        Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent="test", at=world.clock.now()
        )
    )
    web.cookies[COOKIE] = token


@given("the agenda names the clinicians, the type and the rooms")
def agenda_names(world: FakeWorld, scene: Scene) -> None:
    for name, clinician_id in scene.clinicians.items():
        world.agenda.clinicians[clinician_id] = clinician_named(name)
    world.agenda.labels[scene.type] = TYPE_NAME
    world.agenda.labels.update({room_id: name for name, room_id in scene.rooms.items()})


def page_text(scene: Scene) -> str:
    assert scene.page is not None
    return scene.page.content.decode()


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
    caller = scene.caller if who == "caller" else None
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
