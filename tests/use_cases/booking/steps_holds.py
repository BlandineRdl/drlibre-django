"""Steps of visitor holds, codes and verified bookings."""

import dataclasses
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from pytest_bdd import given, parsers, then, when

from drlibre.booking.application.ports.inbound import HoldCreated
from drlibre.identity.domain.session import hash_token
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.errors import DomainError
from tests.builders_booking import (
    patient_user,
)
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import (
    NETWORK,
    Scene,
    at,
    booked,
    typed_patient,
    verified,
)


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
