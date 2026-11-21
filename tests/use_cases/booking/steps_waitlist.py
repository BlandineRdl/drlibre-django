"""Steps of patients and admins joining the waitlist."""

import dataclasses
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pytest_bdd import given, parsers, then, when

from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.builders_booking import patient_user
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import Scene, amend_clinician, amend_type, csv

LEA = "lea@example.org"


def join(
    world: FakeWorld,
    scene: Scene,
    *,
    actor: Id,
    clinician: str | None,
    start: str,
    end: str,
    email: str | None = None,
) -> None:
    try:
        world.app.join_waitlist.execute(
            actor_id=actor,
            appointment_type_id=scene.type,
            clinician_id=scene.clinicians[clinician] if clinician else None,
            from_date=date.fromisoformat(start),
            to_date=date.fromisoformat(end),
            patient_email=email,
        )
    except DomainError as error:
        scene.error = error


def only_entry(world: FakeWorld) -> WaitlistEntry:
    (entry,) = world.waitlist.rows.values()
    return entry


def actor(scene: Scene) -> Id:
    assert scene.actor is not None
    return scene.actor


def add_user(world: FakeWorld, scene: Scene, email: str, role: Role) -> Id:
    user_id = Id()
    world.users.save(patient_user(user_id, email=email, role=role))
    scene.people[email] = user_id
    return user_id


@given(parsers.parse('an active patient "{email}"'))
def active_patient(world: FakeWorld, scene: Scene, email: str) -> None:
    add_user(world, scene, email, Role.PATIENT)


@given("a signed-in admin")
def signed_in_admin(world: FakeWorld, scene: Scene) -> None:
    scene.actor = add_user(world, scene, "admin@example.org", Role.ADMIN)


@given("a signed-in clinician")
def signed_in_clinician(world: FakeWorld, scene: Scene) -> None:
    scene.actor = add_user(world, scene, "clinician@example.org", Role.CLINICIAN)


@given(parsers.parse('the appointment type is in the time zone "{zone}"'))
def type_zone(world: FakeWorld, scene: Scene, zone: str) -> None:
    amend_type(world, scene, time_zone=zone)


@given(parsers.parse('the waitlist choice "{choice}" is unusable'))
def unusable(world: FakeWorld, scene: Scene, choice: str) -> None:
    if choice == "unknown type":
        scene.type = Id()
    elif choice == "inactive type":
        amend_type(world, scene, active=False)
    elif choice == "unknown clinician":
        scene.clinicians["A"] = Id()
    elif choice == "inactive clinician":
        amend_clinician(world, scene, "A", active=False)
    elif choice == "clinician of another department":
        amend_clinician(world, scene, "A", department_id=Id())
    elif choice == "unknown patient":
        world.users.rows.pop(scene.people[LEA])
    else:
        user = world.users.rows[scene.people[LEA]]
        world.users.save(dataclasses.replace(user, active=False))


@given(parsers.parse('"{email}" waits on the waitlist'))
def someone_waits(world: FakeWorld, scene: Scene, email: str) -> None:
    join(
        world,
        scene,
        actor=scene.people[email],
        clinician=None,
        start="2026-11-23",
        end="2026-11-27",
    )


@when(parsers.parse('the patient joins the waitlist with "{name}" from "{start}" to "{end}"'))
def patient_joins_with(world: FakeWorld, scene: Scene, name: str, start: str, end: str) -> None:
    join(world, scene, actor=scene.patient, clinician=name, start=start, end=end)


@when(parsers.parse('the patient joins the waitlist from "{start}" to "{end}"'))
def patient_joins(world: FakeWorld, scene: Scene, start: str, end: str) -> None:
    join(world, scene, actor=scene.patient, clinician=None, start=start, end=end)


@when(parsers.parse('the patient joins the waitlist naming "{email}" from "{start}" to "{end}"'))
def patient_names_someone(world: FakeWorld, scene: Scene, email: str, start: str, end: str) -> None:
    join(world, scene, actor=scene.patient, clinician=None, start=start, end=end, email=email)


@when(parsers.parse('the clinician joins the waitlist from "{start}" to "{end}"'))
def clinician_joins(world: FakeWorld, scene: Scene, start: str, end: str) -> None:
    join(world, scene, actor=actor(scene), clinician=None, start=start, end=end)


@when(
    parsers.parse(
        'the admin adds "{email}" to the waitlist with "{name}" from "{start}" to "{end}"'
    )
)
def admin_adds_with(
    world: FakeWorld, scene: Scene, email: str, name: str, start: str, end: str
) -> None:
    join(world, scene, actor=actor(scene), clinician=name, start=start, end=end, email=email)


@when(parsers.parse('the admin adds "{email}" to the waitlist from "{start}" to "{end}"'))
def admin_adds(world: FakeWorld, scene: Scene, email: str, start: str, end: str) -> None:
    join(world, scene, actor=actor(scene), clinician=None, start=start, end=end, email=email)


@then(parsers.parse('the join is refused as "{code}"'))
def join_refused(scene: Scene, code: str) -> None:
    assert scene.error is not None
    assert scene.error.code.value == code


@then("nothing was written to the waitlist")
def nothing_waitlisted(world: FakeWorld) -> None:
    assert world.waitlist.rows == {}
    assert "booking.waitlist_joined" not in world.audit.actions()


def holds_entry(
    world: FakeWorld, scene: Scene, status: str, patient: Id, clinician: Id | None
) -> None:
    assert scene.error is None, scene.error
    entry = only_entry(world)
    assert (entry.status.value, entry.patient_id, entry.appointment_type_id) == (
        status,
        patient,
        scene.type,
    )
    assert entry.clinician_id == clinician


@then(
    parsers.parse('the waitlist holds one "{status}" entry for the signed-in patient with "{name}"')
)
def patient_entry_with(world: FakeWorld, scene: Scene, status: str, name: str) -> None:
    holds_entry(world, scene, status, scene.patient, scene.clinicians[name])


@then(
    parsers.parse(
        'the waitlist holds one "{status}" entry for the signed-in patient with no clinician'
    )
)
def patient_entry(world: FakeWorld, scene: Scene, status: str) -> None:
    holds_entry(world, scene, status, scene.patient, None)


@then(parsers.parse('the waitlist holds one "{status}" entry for "{email}" with "{name}"'))
def named_entry_with(world: FakeWorld, scene: Scene, status: str, email: str, name: str) -> None:
    holds_entry(world, scene, status, scene.people[email], scene.clinicians[name])


@then(parsers.parse('the waitlist holds one "{status}" entry for "{email}" with no clinician'))
def named_entry(world: FakeWorld, scene: Scene, status: str, email: str) -> None:
    holds_entry(world, scene, status, scene.people[email], None)


@then(parsers.parse('the entry waits from "{start}" to "{end}" in "{zone}"'))
def window(world: FakeWorld, start: str, end: str, zone: str) -> None:
    local = ZoneInfo(zone)
    entry = only_entry(world)
    assert entry.earliest == datetime.fromisoformat(start).replace(tzinfo=local)
    assert entry.latest == datetime.fromisoformat(end).replace(tzinfo=local)


@then("the admin list shows that entry")
def admin_list(world: FakeWorld) -> None:
    page = world.app.waitlist_queries.page("", PageRequest())
    assert [r.entry for r in page.items] == [only_entry(world)]
    assert page.total == 1


@then(parsers.parse('the patient\'s own list shows "{statuses}", newest first'))
def own_list(world: FakeWorld, scene: Scene, statuses: str) -> None:
    rows = world.app.waitlist_queries.own_entries(scene.patient)
    assert [r.entry.status.value for r in rows] == csv(statuses)
    assert all(r.entry.patient_id == scene.patient for r in rows)
    created = [r.entry.created_at for r in rows]
    assert created == sorted(created, reverse=True)


def audited_with_ids_only(world: FakeWorld, by: Id, action: str) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert entry.actor == by
    assert entry.entity_type == "waitlist_entry"
    for _, value in entry.metadata:
        assert isinstance(value, str)
        uuid.UUID(value)


@then(parsers.parse('the audit holds "{action}" by the signed-in patient with ids only'))
def audited_patient(world: FakeWorld, scene: Scene, action: str) -> None:
    audited_with_ids_only(world, scene.patient, action)


@then(parsers.parse('the audit holds "{action}" by the admin with ids only'))
def audited_admin(world: FakeWorld, scene: Scene, action: str) -> None:
    audited_with_ids_only(world, actor(scene), action)
