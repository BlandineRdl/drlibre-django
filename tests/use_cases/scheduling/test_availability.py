import dataclasses
from collections.abc import Callable
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import Container, wire
from drlibre.organisation.infrastructure.schedule_and_booking_dependents import (
    ScheduleAndBookingDependents,
)
from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    Clinician,
    Room,
    StoredSlot,
)
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_scheduling import appointment
from tests.builders_web import fake_clinician, signed_in
from tests.fakes.audit_log import AuditLogUnavailableError
from tests.fakes.world import FakeWorld

scenarios(
    "../../features/scheduling/le_praticien_gere_ses_plages_hebdomadaires.feature",
    "../../features/scheduling/le_praticien_declare_ses_absences.feature",
)


@dataclasses.dataclass
class Person:
    user_id: Id
    profile_id: Id


class Outcome:
    def __init__(self) -> None:
        self.tz = ZoneInfo("Europe/Paris")
        self.department = Id()
        self.people: dict[str, Person] = {}
        self.rooms: dict[str, Id] = {}
        self.slots_before: list[StoredSlot] = []
        self.error: DomainError | None = None
        self.clients: dict[str, Client] = {}
        self.path = ""
        self.body = ""

    def local(self, raw: str) -> datetime:
        return datetime.fromisoformat(raw).replace(tzinfo=self.tz)


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


def attempt(outcome: Outcome, write: Callable[[], object]) -> None:
    try:
        write()
    except DomainError as error:
        outcome.error = error
    except AuditLogUnavailableError:
        # The unit of work rolls back; Then steps check nothing was written.
        pass


def rule_fields(weekday: str, start: str, end: str, step: str, room: Id | None) -> dict[str, str]:
    fields = {"weekday": weekday, "start": start, "end": end, "step_minutes": step}
    return fields | ({"room_id": str(room)} if room else {})


def only_rule(world: FakeWorld, person: Person) -> Id:
    (found,) = world.availability_queries.rules_of(person.profile_id)
    return found.id


@given(parsers.parse('a hospital of time zone "{time_zone}" with a department'))
def hospital(outcome: Outcome, time_zone: str) -> None:
    outcome.tz = ZoneInfo(time_zone)


@given(parsers.parse('the clinicians "{first}" and "{second}" in that department'))
def clinicians(world: FakeWorld, outcome: Outcome, first: str, second: str) -> None:
    for name in (first, second):
        person = Person(Id(), Id())
        outcome.people[name] = person
        clinician = Clinician(person.profile_id, outcome.department, outcome.tz.key, active=True)
        world.scheduling_directory.clinicians[clinician.id] = clinician
        world.scheduling_directory.profile_of_user[person.user_id] = person.profile_id


@given(parsers.parse("an active appointment type of {minutes:d} minutes in that department"))
def appointment_type(world: FakeWorld, outcome: Outcome, minutes: int) -> None:
    kind = AppointmentType(Id(), outcome.department, minutes, 0, True, outcome.tz.key)
    world.scheduling_directory.types[kind.id] = kind


@given(parsers.parse('today is "{day}"'))
def today(world: FakeWorld, outcome: Outcome, day: str) -> None:
    world.clock.at = datetime.combine(date.fromisoformat(day), time(8), tzinfo=outcome.tz)


def add_room(
    world: FakeWorld, outcome: Outcome, name: str, *, department: Id, active: bool
) -> None:
    room = build.room(department, name=name, active=active)
    world.rooms.save(room)
    world.scheduling_directory.rooms[room.id] = Room(room.id, department, active)
    outcome.rooms[name] = room.id


@given(parsers.parse('an active room "{name}" in that department'))
def active_room(world: FakeWorld, outcome: Outcome, name: str) -> None:
    add_room(world, outcome, name, department=outcome.department, active=True)


@given(parsers.parse('an inactive room "{name}" in that department'))
def inactive_room(world: FakeWorld, outcome: Outcome, name: str) -> None:
    add_room(world, outcome, name, department=outcome.department, active=False)


@given(parsers.parse('an active room "{name}" in another department'))
def foreign_room(world: FakeWorld, outcome: Outcome, name: str) -> None:
    add_room(world, outcome, name, department=Id(), active=True)


@given(parsers.parse('an unknown room "{name}"'))
def unknown_room(outcome: Outcome, name: str) -> None:
    outcome.rooms[name] = Id()


RULE = (
    r'"(?P<name>[^"]+)" (?P<verb>saves|saved) a rule on weekday "(?P<weekday>[^"]*)" from '
    r'"(?P<start>[^"]*)" to "(?P<end>[^"]*)" every "(?P<step>[^"]*)" minutes'
    r'(?: in room "(?P<room>[^"]+)")?$'
)


@given(parsers.re(RULE))
@when(parsers.re(RULE))
def saves_rule(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    verb: str,
    weekday: str,
    start: str,
    end: str,
    step: str,
    room: str | None,
) -> None:
    fields = rule_fields(weekday, start, end, step, outcome.rooms[room] if room else None)
    actor = outcome.people[name].user_id
    use_case = world.app.save_availability_rule
    attempt(outcome, lambda: use_case.execute(actor=actor, rule_id=None, fields=fields))
    if verb == "saved":
        assert outcome.error is None


EDIT = (
    r'"(?P<name>[^"]+)" edits (?:that rule|the rule of "(?P<owner>[^"]+)") to weekday '
    r'"(?P<weekday>[^"]*)" from "(?P<start>[^"]*)" to "(?P<end>[^"]*)" every "(?P<step>[^"]*)" '
    r"minutes$"
)


@when(parsers.re(EDIT))
def edits_rule(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    owner: str | None,
    weekday: str,
    start: str,
    end: str,
    step: str,
) -> None:
    rule_id = only_rule(world, outcome.people[owner or name])
    fields = rule_fields(weekday, start, end, step, None)
    actor = outcome.people[name].user_id
    use_case = world.app.save_availability_rule
    attempt(outcome, lambda: use_case.execute(actor=actor, rule_id=rule_id, fields=fields))


@when(parsers.re(r'"(?P<name>[^"]+)" deletes (?:that rule|the rule of "(?P<owner>[^"]+)")$'))
def deletes_rule(world: FakeWorld, outcome: Outcome, name: str, owner: str | None) -> None:
    rule_id = only_rule(world, outcome.people[owner or name])
    actor = outcome.people[name].user_id
    use_case = world.app.delete_availability_rule
    attempt(outcome, lambda: use_case.execute(actor=actor, rule_id=rule_id))


@when(parsers.parse('"{name}" deletes an unknown rule'))
def deletes_unknown_rule(world: FakeWorld, outcome: Outcome, name: str) -> None:
    actor = outcome.people[name].user_id
    use_case = world.app.delete_availability_rule
    attempt(outcome, lambda: use_case.execute(actor=actor, rule_id=Id()))


TIME_OFF = (
    r'"(?P<name>[^"]+)" (?P<verb>records|recorded) a time off from "(?P<start>[^"]*)" to '
    r'"(?P<end>[^"]*)"(?: because "(?P<reason>[^"]*)")?'
    r"(?P<long> with a reason of 201 characters)?$"
)


@given(parsers.re(TIME_OFF))
@when(parsers.re(TIME_OFF))
def records_time_off(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    verb: str,
    start: str,
    end: str,
    reason: str | None,
    long: str | None,
) -> None:
    fields = {"start": start, "end": end, "reason": "x" * 201 if long else reason or ""}
    actor = outcome.people[name].user_id
    use_case = world.app.record_time_off
    attempt(outcome, lambda: use_case.execute(actor=actor, fields=fields))
    if verb == "recorded":
        assert outcome.error is None


@when(
    parsers.re(r'"(?P<name>[^"]+)" deletes (?:that time off|the time off of "(?P<owner>[^"]+)")$')
)
def deletes_time_off(world: FakeWorld, outcome: Outcome, name: str, owner: str | None) -> None:
    person = outcome.people[owner or name]
    (found,) = world.availability_queries.time_offs_of(person.profile_id)
    actor = outcome.people[name].user_id
    use_case = world.app.delete_time_off
    attempt(outcome, lambda: use_case.execute(actor=actor, time_off_id=found.id))


@given(parsers.parse('"{name}" has a "{status}" appointment from "{start}" to "{end}"'))
def has_appointment(
    world: FakeWorld, outcome: Outcome, name: str, status: str, start: str, end: str
) -> None:
    clinician = outcome.people[name].profile_id
    row = appointment(clinician, outcome.local(start), outcome.local(end), status=status)
    world.clinician_appointments.rows.append(row)


@given("the audit log is unavailable")
def audit_unavailable(world: FakeWorld, outcome: Outcome) -> None:
    outcome.slots_before = list(world.slots.rows)
    world.audit.failing = True


@when(parsers.parse('the admin deletes the room "{name}"'))
def admin_deletes_room(world: FakeWorld, outcome: Outcome, name: str) -> None:
    usage = ScheduleAndBookingDependents(
        usage=world.availability_queries, appointments=world.booking_queries
    )
    app = wire(dataclasses.replace(world.adapters(), schedule=usage))
    room_id = outcome.rooms[name]
    attempt(outcome, lambda: app.delete_room.execute(actor=None, record_id=room_id))


@then(parsers.parse('"{name}" has the rules "{labels}"'))
def has_rules(world: FakeWorld, outcome: Outcome, name: str, labels: str) -> None:
    rules = world.availability_queries.rules_of(outcome.people[name].profile_id)
    assert [r.label for r in rules] == [label.strip() for label in labels.split(",")]


@then(parsers.parse('"{name}" has no rule'))
def has_no_rule(world: FakeWorld, outcome: Outcome, name: str) -> None:
    assert world.availability_queries.rules_of(outcome.people[name].profile_id) == ()


@then(parsers.parse('the rule of "{name}" has a {step:d}-minute step and no room'))
def rule_step(world: FakeWorld, outcome: Outcome, name: str, step: int) -> None:
    (found,) = world.availability_queries.rules_of(outcome.people[name].profile_id)
    assert (found.step_minutes, found.room_id) == (step, None)


@then(parsers.parse('the rule of "{name}" is in room "{room}"'))
def rule_room(world: FakeWorld, outcome: Outcome, name: str, room: str) -> None:
    (found,) = world.availability_queries.rules_of(outcome.people[name].profile_id)
    assert found.room_id == outcome.rooms[room]


@then(parsers.parse('the rule of "{name}" is valid from "{day}" with no end date'))
def rule_validity(world: FakeWorld, outcome: Outcome, name: str, day: str) -> None:
    (found,) = world.availability_queries.rules_of(outcome.people[name].profile_id)
    assert (found.valid_from, found.valid_to) == (date.fromisoformat(day), None)


def local_starts(world: FakeWorld, outcome: Outcome, person: Person, day: str) -> list[str]:
    starts = {
        r.slot.start.astimezone(outcome.tz)
        for r in world.slots.rows
        if r.clinician_id == person.profile_id
    }
    return [s.strftime("%H:%M") for s in sorted(starts) if s.date().isoformat() == day]


@then(parsers.parse('the stored slots of "{name}" on "{day}" start at "{starts}" local time'))
def stored_slots(world: FakeWorld, outcome: Outcome, name: str, day: str, starts: str) -> None:
    found = local_starts(world, outcome, outcome.people[name], day)
    assert found == [s.strip() for s in starts.split(",")]


@then(parsers.parse('the stored slots of "{name}" are unchanged'))
def slots_unchanged(world: FakeWorld, outcome: Outcome, name: str) -> None:
    assert outcome.slots_before
    assert world.slots.rows == outcome.slots_before


def _local(outcome: Outcome, instant: datetime) -> str:
    return f"{instant.astimezone(outcome.tz):%Y-%m-%dT%H:%M}"


@then(parsers.parse('"{name}" has the time off "{periods}"'))
def has_time_off(world: FakeWorld, outcome: Outcome, name: str, periods: str) -> None:
    found = world.availability_queries.time_offs_of(outcome.people[name].profile_id)
    shown = [f"{_local(outcome, t.start)} → {_local(outcome, t.end)}" for t in found]
    assert shown == [p.strip() for p in periods.split(",")]


@then(parsers.parse('"{name}" has no time off'))
def has_no_time_off(world: FakeWorld, outcome: Outcome, name: str) -> None:
    assert world.availability_queries.time_offs_of(outcome.people[name].profile_id) == ()


@then(parsers.parse('the time off of "{name}" starts at "{instant}"'))
def time_off_instant(world: FakeWorld, outcome: Outcome, name: str, instant: str) -> None:
    (found,) = world.availability_queries.time_offs_of(outcome.people[name].profile_id)
    assert found.start == datetime.fromisoformat(instant)
    assert found.start.tzinfo is UTC


@then(parsers.parse('the appointment of "{name}" is still "{status}"'))
def appointment_kept(world: FakeWorld, outcome: Outcome, name: str, status: str) -> None:
    clinician = outcome.people[name].profile_id
    assert [a.status for c, a in world.clinician_appointments.rows if c == clinician] == [status]
    assert outcome.error is None


@then(
    parsers.re(
        r'the write is refused as invalid on "(?P<field>[^"]+)"(?: naming "(?P<text>[^"]+)")?$'
    )
)
def refused_on_field(outcome: Outcome, field: str, text: str | None) -> None:
    assert outcome.error is not None
    assert outcome.error.code == "invalid_input"
    fields = {f["field"]: f["message"] for f in outcome.error.details["fields"]}
    assert field in fields
    assert text is None or text in fields[field]


@then(parsers.re(r'the write is refused as "(?P<code>[a-z_]+)"$'))
def refused_as(outcome: Outcome, code: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code == code


@then(
    parsers.parse(
        'the write is refused as "has_dependents" listing the availability rule "{label}"'
    )
)
def refused_with_rule(outcome: Outcome, label: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code == "has_dependents"
    listed = [(d["kind"], d["label"]) for d in outcome.error.details["dependents"]]
    assert listed == [("availability_rule", label)]


@then(parsers.parse('the audit holds "{actions}" by "{name}"'))
def audit_holds(world: FakeWorld, outcome: Outcome, actions: str, name: str) -> None:
    assert world.audit.actions() == [a.strip() for a in actions.split(",")]
    assert {e.actor for e in world.audit.entries} == {outcome.people[name].user_id}


@then(parsers.parse('the audit metadata holds only "{keys}"'))
def audit_keys(world: FakeWorld, keys: str) -> None:
    found = {key for e in world.audit.entries for key, _ in e.metadata}
    assert found <= {k.strip() for k in keys.split(",")}


@then(parsers.parse('the "{action}" entry names the changed fields "{names}"'))
def audit_changed(world: FakeWorld, action: str, names: str) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert dict(entry.metadata)["changed"] == tuple(n.strip() for n in names.split(","))


@then(parsers.parse('no audit entry mentions "{text}"'))
def audit_silent(world: FakeWorld, text: str) -> None:
    assert world.audit.entries
    assert all(text not in repr(e) for e in world.audit.entries)


def web(world: FakeWorld, outcome: Outcome, name: str) -> Client:
    """The clinician's workspace over the fake wiring, signed in on first use."""
    if name not in outcome.clients:
        person = outcome.people[name]
        user = fake_clinician(
            world,
            user_id=person.user_id,
            profile_id=person.profile_id,
            department_id=outcome.department,
            time_zone=outcome.tz.key,
            name=name,
        )
        outcome.clients[name] = signed_in(world, user)
    return outcome.clients[name]


@when(parsers.parse('"{name}" opens the page "{path}"'))
def opens_page(
    world: FakeWorld, outcome: Outcome, fake_container: Container, name: str, path: str
) -> None:
    response = web(world, outcome, name).get(path)
    assert response.status_code == 200
    outcome.body = response.content.decode()


@when(parsers.re(r'"(?P<name>[^"]+)" opens the deletion of that (?P<kind>rule|time off)$'))
def opens_deletion(
    world: FakeWorld, outcome: Outcome, fake_container: Container, name: str, kind: str
) -> None:
    clinician = outcome.people[name].profile_id
    if kind == "rule":
        (found,) = world.availability_queries.rules_of(clinician)
        outcome.path = f"/workspace/availability/{found.id}/delete"
    else:
        (off,) = world.availability_queries.time_offs_of(clinician)
        outcome.path = f"/workspace/time-off/{off.id}/delete"
    outcome.body = web(world, outcome, name).get(outcome.path).content.decode()


@when(parsers.parse('"{name}" confirms the deletion'))
def confirms_deletion(world: FakeWorld, outcome: Outcome, name: str) -> None:
    assert web(world, outcome, name).post(outcome.path).status_code == 302


@then("the page asks for confirmation")
def asks_confirmation(outcome: Outcome) -> None:
    assert "Cette action est définitive." in outcome.body


@then(parsers.parse('the page names the time zone "{time_zone}"'))
def names_time_zone(outcome: Outcome, time_zone: str) -> None:
    assert f"Fuseau : {time_zone}" in outcome.body or f"({time_zone})" in outcome.body


@then(parsers.parse('the page shows "{text}"'))
def page_shows(outcome: Outcome, text: str) -> None:
    assert text in outcome.body
