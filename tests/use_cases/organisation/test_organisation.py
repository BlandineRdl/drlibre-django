from datetime import date
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import Container
from drlibre.identity.domain.user import Email, Role, User
from drlibre.organisation.application.ports.outbound import Clinician
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest
from drlibre.shared_kernel.validation import parse_id
from tests.fakes.organisation import InMemoryRecords
from tests.fakes.world import FakeWorld

scenarios("../../features/organisation")

KIND = r"(?P<kind>hospital|specialty|department|room|appointment type)"
ADMIN = Id()


def kind_of(raw: str) -> str:
    return raw.replace(" ", "_")


class Outcome:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.mark = 0
        self.path = ""
        self.people: dict[str, Id] = {}
        self.body = ""


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


def store(world: FakeWorld, kind: str) -> InMemoryRecords:
    return {
        "hospital": world.hospitals,
        "specialty": world.specialties,
        "department": world.departments,
        "room": world.rooms,
        "appointment_type": world.appointment_types,
    }[kind]


def find(world: FakeWorld, kind: str, code: str) -> Any:
    return next((r for r in store(world, kind).rows.values() if r.code == code), None)


def last_id(world: FakeWorld, kind: str) -> str:
    rows = list(store(world, kind).rows.values())
    return str(rows[-1].id) if rows else ""


def defaults(world: FakeWorld, kind: str, code: str) -> dict[str, str]:
    common = {"name": f"Nom {code}", "code": code, "active": "on"}
    return {
        "hospital": {
            **common,
            "street": "1 rue de la Paix",
            "postal_code": "59000",
            "city": "Roubaix",
            "country": "France",
            "phone": "+33 3 20 00 00 00",
            "time_zone": "Europe/Paris",
        },
        "specialty": common,
        "department": {**common, "hospital_id": last_id(world, "hospital")},
        "room": {
            **common,
            "department_id": last_id(world, "department"),
            "floor": "1",
            "capacity": "2",
        },
        "appointment_type": {
            **common,
            "department_id": last_id(world, "department"),
            "duration_minutes": "30",
            "buffer_minutes": "5",
            "colour": "#336699",
            "needs_room": "on",
            "bookable_online": "on",
        },
    }[kind]


def save(
    world: FakeWorld,
    outcome: Outcome,
    kind: str,
    fields: dict[str, str],
    record_id: Id | None = None,
) -> None:
    world.audit.entries.clear()
    use_case = getattr(world.app, f"save_{kind}")
    try:
        use_case.execute(actor=ADMIN, record_id=record_id, fields=fields)
        outcome.error = None
    except Exception as error:
        outcome.error = error


def delete(world: FakeWorld, outcome: Outcome, kind: str, record_id: Id) -> None:
    world.audit.entries.clear()
    try:
        getattr(world.app, f"delete_{kind}").execute(actor=ADMIN, record_id=record_id)
    except DomainError as error:
        outcome.error = error


@given(parsers.re(rf'an? {KIND} "(?P<code>[^"]+)" exists$'))
def exists(world: FakeWorld, outcome: Outcome, kind: str, code: str) -> None:
    save(world, outcome, kind_of(kind), defaults(world, kind_of(kind), code))
    assert outcome.error is None


@given(
    parsers.re(
        rf'an? {KIND} "(?P<code>[^"]+)" exists in '
        r'(?P<parent>hospital|department) "(?P<parent_code>[^"]+)"'
    )
)
def exists_in(
    world: FakeWorld, outcome: Outcome, kind: str, code: str, parent: str, parent_code: str
) -> None:
    fields = defaults(world, kind_of(kind), code)
    fields[f"{parent}_id"] = str(find(world, parent, parent_code).id)
    save(world, outcome, kind_of(kind), fields)
    assert outcome.error is None


@given("the audit log is down")
def audit_down(world: FakeWorld) -> None:
    world.audit.failing = True


@given(parsers.parse('the room "{code}" is used by an availability rule'))
def room_used(world: FakeWorld, code: str) -> None:
    world.schedule.by_room[find(world, "room", code).id] = (
        Dependent("availability_rule", Id(), "Lundi 09:00"),
    )


@given(parsers.parse('the appointment type "{code}" has an appointment'))
def type_used(world: FakeWorld, code: str) -> None:
    label = f"RDV {date(2026, 12, 1).isoformat()}"
    world.schedule.by_appointment_type[find(world, "appointment_type", code).id] = (
        Dependent("appointment", Id(), label),
    )


@when(parsers.re(rf'the admin saves an? {KIND} "(?P<code>[^"]+)" named "(?P<name>[^"]+)"'))
def saves_named(world: FakeWorld, outcome: Outcome, kind: str, code: str, name: str) -> None:
    save(world, outcome, kind_of(kind), {**defaults(world, kind_of(kind), code), "name": name})


@when(
    parsers.re(
        rf'the admin saves an? {KIND} "(?P<code>[^"]+)" with (?P<field>\w+) "(?P<value>[^"]*)"$'
    )
)
def saves_with(
    world: FakeWorld, outcome: Outcome, kind: str, code: str, field: str, value: str
) -> None:
    save(world, outcome, kind_of(kind), {**defaults(world, kind_of(kind), code), field: value})


@when(
    parsers.re(r'the admin saves a department "(?P<code>[^"]+)" in hospital "(?P<hospital>[^"]+)"')
)
def saves_department(world: FakeWorld, outcome: Outcome, code: str, hospital: str) -> None:
    fields = {
        **defaults(world, "department", code),
        "hospital_id": str(find(world, "hospital", hospital).id),
    }
    save(world, outcome, "department", fields)


@when(
    parsers.re(
        r'the admin saves a room "(?P<code>[^"]+)" in department "(?P<dept>[^"]+)" '
        r'with equipment "(?P<equipment>[^"]*)"'
    )
)
def saves_room(world: FakeWorld, outcome: Outcome, code: str, dept: str, equipment: str) -> None:
    fields = {
        **defaults(world, "room", code),
        "department_id": str(find(world, "department", dept).id),
        "equipment": equipment,
    }
    save(world, outcome, "room", fields)


@when(
    parsers.parse('the admin edits the hospital "{code}" setting name "{name}" and city "{city}"')
)
def edits_hospital(world: FakeWorld, outcome: Outcome, code: str, name: str, city: str) -> None:
    hospital = find(world, "hospital", code)
    fields = {**defaults(world, "hospital", code), "name": name, "city": city}
    save(world, outcome, "hospital", fields, hospital.id)


@when("the admin edits an unknown hospital")
def edits_unknown(world: FakeWorld, outcome: Outcome) -> None:
    save(world, outcome, "hospital", defaults(world, "hospital", "GHOST"), Id())


@when(parsers.re(rf'the admin deletes the {KIND} "(?P<code>[^"]+)"'))
def deletes(world: FakeWorld, outcome: Outcome, kind: str, code: str) -> None:
    delete(world, outcome, kind_of(kind), find(world, kind_of(kind), code).id)


@when("the admin deletes an unknown room")
def deletes_unknown(world: FakeWorld, outcome: Outcome) -> None:
    delete(world, outcome, "room", Id())


@then(parsers.parse('the hospital "{code}" is listed with time zone "{zone}"'))
def hospital_listed(world: FakeWorld, outcome: Outcome, code: str, zone: str) -> None:
    assert outcome.error is None
    page = world.app.reference_queries.hospitals(PageRequest())
    assert [(h.code, h.time_zone) for h in page.items] == [(code, zone)]


@then(parsers.re(rf'the {KIND} "(?P<code>[^"]+)" is listed'))
def listed(world: FakeWorld, outcome: Outcome, kind: str, code: str) -> None:
    assert outcome.error is None
    method = {"appointment_type": "appointment_types", "specialty": "specialties"}.get(
        kind_of(kind), f"{kind_of(kind)}s"
    )
    page = getattr(world.app.reference_queries, method)(PageRequest(search=code.lower()))
    assert [r.code for r in page.items] == [code]


@then(parsers.parse('the audit holds "{action}" for "{code}"'))
def audited(world: FakeWorld, action: str, code: str) -> None:
    kind = action.split(".")[0]
    [entry] = world.audit.entries
    assert entry.action == action
    assert entry.actor == ADMIN
    record = find(world, kind, code)
    if record is not None:
        assert entry.entity_id == record.id


@then(parsers.parse('the audit holds "{action}" for "{code}" changing "{fields}"'))
def audited_changes(world: FakeWorld, action: str, code: str, fields: str) -> None:
    [entry] = world.audit.entries
    assert entry.action == action
    assert entry.entity_id == find(world, "hospital", code).id
    assert dict(entry.metadata)["changed"] == tuple(fields.split(","))


@then(parsers.parse('the save is refused as invalid on "{field}"'))
def invalid_on(outcome: Outcome, field: str) -> None:
    assert isinstance(outcome.error, DomainError)
    assert outcome.error.code.value == "invalid_input"
    assert [f["field"] for f in outcome.error.details["fields"]] == [field]


@then(parsers.parse('the save is refused as "{code}"'))
@then(parsers.parse('the delete is refused as "{code}"'))
def refused_as(outcome: Outcome, code: str) -> None:
    assert isinstance(outcome.error, DomainError)
    assert outcome.error.code.value == code


@then("the save fails")
def save_fails(outcome: Outcome) -> None:
    assert outcome.error is not None


@then(parsers.re(rf'no {KIND} "(?P<code>[^"]+)" is stored'))
def not_stored(world: FakeWorld, kind: str, code: str) -> None:
    assert find(world, kind_of(kind), code) is None


@then("nothing is audited")
def nothing_audited(world: FakeWorld) -> None:
    assert world.audit.entries == []


@then(parsers.parse('the room "{code}" has equipment "{equipment}"'))
def room_equipment(world: FakeWorld, code: str, equipment: str) -> None:
    assert find(world, "room", code).equipment == tuple(equipment.split("|"))


@then(parsers.parse('the appointment type "{code}" has colour "{colour}"'))
def type_colour(world: FakeWorld, code: str, colour: str) -> None:
    assert find(world, "appointment_type", code).colour == colour


@then(parsers.re(r"the (?:delete|move) is refused listing (?P<listing>.+)$"))
def refused_listing(outcome: Outcome, listing: str) -> None:
    assert isinstance(outcome.error, DomainError)
    assert outcome.error.code.value == "has_dependents"
    expected = []
    for part in listing.split(" and "):
        kind, label = part.split(" ", 1)
        expected.append((kind, label.strip('"')))
    listed = [(d["kind"], d["label"]) for d in outcome.error.details["dependents"]]
    assert len(listed) == len(expected)
    for (kind, label), (expected_kind, expected_label) in zip(listed, expected, strict=True):
        assert kind == expected_kind
        assert expected_label in label


PLURAL = {
    "hospital": "hospitals",
    "specialty": "specialties",
    "department": "departments",
    "room": "rooms",
    "appointment_type": "appointment_types",
}
SLUG = {"appointment_type": "appointment-types"}


@pytest.fixture
def console(world: FakeWorld, fake_container: Container) -> Client:
    """The real console views, served over the fake wiring to a signed-in admin."""
    at = world.clock.now()
    admin = User(
        id=Id(),
        email=Email("console-admin@example.org"),
        full_name="Admin",
        role=Role.ADMIN,
        active=True,
        password_hash=world.hasher.hash("admin-password-1"),
        must_change_password=False,
        last_login_at=None,
        created_at=at,
        updated_at=at,
    )
    world.users.save(admin)
    signed = world.app.sign_in.execute(
        email=admin.email.value, password="admin-password-1", user_agent="pytest"
    )
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = signed.token
    return client


@given(
    parsers.re(
        rf"(?P<count>\d+) {KIND} records exist, (?P<matching>\d+) of them named with "
        r'"(?P<word>[^"]+)"'
    )
)
def many_records(
    world: FakeWorld, outcome: Outcome, count: str, kind: str, matching: str, word: str
) -> None:
    for number in range(int(count)):
        name = f"{word} {number}" if number < int(matching) else f"Autre {number}"
        record_code = f"X{number:03}"
        save(
            world,
            outcome,
            kind_of(kind),
            {**defaults(world, kind_of(kind), record_code), "name": name},
        )
        assert outcome.error is None


@when(
    parsers.re(rf"the admin lists the {KIND} records on page (?P<number>\d+)"),
    target_fixture="page",
)
def lists_page(world: FakeWorld, kind: str, number: str) -> Page[Any]:
    method = getattr(world.app.reference_queries, PLURAL[kind_of(kind)])
    return method(PageRequest(number=int(number)))


@when(
    parsers.re(rf'the admin lists the {KIND} records searching "(?P<text>[^"]+)"'),
    target_fixture="page",
)
def lists_search(world: FakeWorld, kind: str, text: str) -> Page[Any]:
    method = getattr(world.app.reference_queries, PLURAL[kind_of(kind)])
    return method(PageRequest(search=text))


@then(parsers.re(r"the page shows (?P<rows>\d+) rows out of (?P<total>\d+)"))
def page_shows(page: Page[Any], rows: str, total: str) -> None:
    assert (len(page.items), page.total) == (int(rows), int(total))


@given("the admin is signed in on the console")
def signed_in_console(console: Client) -> None:
    assert console.get("/console/").status_code == 200


@when(parsers.re(rf'the admin opens the deletion of the {KIND} "(?P<code>[^"]+)"'))
def opens_deletion(
    world: FakeWorld, outcome: Outcome, console: Client, kind: str, code: str
) -> None:
    record = find(world, kind_of(kind), code)
    outcome.path = f"/console/{SLUG.get(kind_of(kind), PLURAL[kind_of(kind)])}/{record.id}/delete"
    outcome.body = console.get(outcome.path).content.decode()


@then(parsers.re(rf'the deletion asks for confirmation and keeps the {KIND} "(?P<code>[^"]+)"'))
def asks_confirmation(world: FakeWorld, outcome: Outcome, kind: str, code: str) -> None:
    assert "Cette action est définitive." in outcome.body
    assert find(world, kind_of(kind), code) is not None


@when("the admin confirms the deletion")
def confirms_deletion(outcome: Outcome, console: Client) -> None:
    assert console.post(outcome.path).status_code == 302


@given(parsers.re(r'an? (?P<state>active|inactive) clinician "(?P<name>[^"]+)"'))
def clinician(world: FakeWorld, outcome: Outcome, state: str, name: str) -> None:
    user_id = Id()
    outcome.people[name] = user_id
    if state == "active":
        world.staff.active_clinicians[user_id] = Clinician(user_id, name)


@given(parsers.re(r'an inactive room "(?P<code>[^"]+)" exists in department "(?P<dept>[^"]+)"'))
def inactive_room(world: FakeWorld, outcome: Outcome, code: str, dept: str) -> None:
    fields = {
        **defaults(world, "room", code),
        "department_id": str(find(world, "department", dept).id),
    }
    save(world, outcome, "room", {**fields, "active": ""})


def profile_fields(
    world: FakeWorld, name: str, dept: str, specialty: str, room: str
) -> dict[str, str]:
    return {
        "department_id": str(find(world, "department", dept).id),
        "specialty_id": str(find(world, "specialty", specialty).id),
        "default_room_id": str(find(world, "room", room).id),
        "title": f"Dr {name}",
        "bio": "",
        "weight": "",
    }


def attach(world: FakeWorld, outcome: Outcome, name: str, fields: dict[str, str]) -> None:
    outcome.mark = len(world.audit.entries)
    user_id = outcome.people.get(name, Id())
    try:
        world.app.attach_clinician_profile.execute(actor=ADMIN, user_id=str(user_id), fields=fields)
        outcome.error = None
    except DomainError as error:
        outcome.error = error


PROFILE = (
    r'"(?P<name>[^"]+)" in department "(?P<dept>[^"]+)" with specialty "(?P<specialty>[^"]+)" '
    r'and default room "(?P<room>[^"]+)"'
)


@given(parsers.re(rf"{PROFILE.replace(' in department', ' has a profile in department')}$"))
def has_profile(
    world: FakeWorld, outcome: Outcome, name: str, dept: str, specialty: str, room: str
) -> None:
    attach(world, outcome, name, profile_fields(world, name, dept, specialty, room))
    assert outcome.error is None


@when(parsers.re(rf"the admin attaches a profile to {PROFILE}$"))
def attaches(
    world: FakeWorld, outcome: Outcome, name: str, dept: str, specialty: str, room: str
) -> None:
    attach(world, outcome, name, profile_fields(world, name, dept, specialty, room))


@when(
    parsers.re(
        r'the admin attaches a profile to "(?P<name>[^"]+)" with (?P<field>\w+) "(?P<value>[^"]*)"$'
    )
)
def attaches_with(world: FakeWorld, outcome: Outcome, name: str, field: str, value: str) -> None:
    fields = profile_fields(world, name, "CARD", "CARDIO", "R101")
    room = find(world, "room", value) if field == "default_room_id" else None
    fields[field] = str(room.id) if room else value
    attach(world, outcome, name, fields)


@when(parsers.parse('the admin moves the room "{code}" to department "{dept}"'))
def moves_room(world: FakeWorld, outcome: Outcome, code: str, dept: str) -> None:
    room = find(world, "room", code)
    fields = {
        **defaults(world, "room", code),
        "department_id": str(find(world, "department", dept).id),
    }
    save(world, outcome, "room", fields, room.id)


@when(parsers.parse('the admin edits the profile of "{name}" setting weight "{weight}"'))
def edits_profile(world: FakeWorld, outcome: Outcome, name: str, weight: str) -> None:
    profile = world.profiles.for_user(outcome.people[name])
    assert profile is not None
    outcome.mark = len(world.audit.entries)
    fields = {**record_text(profile), "weight": weight}
    world.app.edit_clinician_profile.execute(actor=ADMIN, profile_id=profile.id, fields=fields)


def record_text(profile: Any) -> dict[str, str]:
    return {
        "department_id": str(profile.department_id),
        "specialty_id": str(profile.specialty_id),
        "default_room_id": str(profile.default_room_id or ""),
        "title": profile.title,
        "bio": profile.bio,
        "weight": str(profile.weight),
    }


@then(
    parsers.re(
        r'the profile of "(?P<name>[^"]+)" is in department "(?P<dept>[^"]+)" with specialty '
        r'"(?P<specialty>[^"]+)", default room "(?P<room>[^"]+)" and weight (?P<weight>\d+)'
    )
)
def profile_is(
    world: FakeWorld, outcome: Outcome, name: str, dept: str, specialty: str, room: str, weight: str
) -> None:
    assert outcome.error is None
    profile = world.profiles.for_user(outcome.people[name])
    assert profile is not None
    assert profile.department_id == find(world, "department", dept).id
    assert profile.specialty_id == find(world, "specialty", specialty).id
    assert profile.default_room_id == find(world, "room", room).id
    assert profile.weight == int(weight)


@then(parsers.parse('the profile of "{name}" has weight {weight:d}'))
def profile_weight(world: FakeWorld, outcome: Outcome, name: str, weight: int) -> None:
    profile = world.profiles.for_user(outcome.people[name])
    assert profile is not None
    assert profile.weight == weight


@then(parsers.parse('the audit holds "{action}" holding only ids'))
def audited_ids(world: FakeWorld, outcome: Outcome, action: str) -> None:
    [entry] = world.audit.entries[outcome.mark :]
    assert entry.action == action
    for _, value in entry.metadata:
        values = value if isinstance(value, tuple) else (value,)
        assert all(parse_id(str(v)) is not None or str(v).isidentifier() for v in values)
