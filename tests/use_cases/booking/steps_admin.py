"""Steps of an admin acting on any appointment."""

from pytest_bdd import parsers, then, when

from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_changes import change
from tests.use_cases.booking.steps_clinician import _STATUS_USE_CASES
from tests.use_cases.booking.steps_waitlist import actor
from tests.use_cases.booking.support import Scene, at, csv, mine


def admin_books(
    world: FakeWorld,
    scene: Scene,
    start: str,
    *,
    clinician: str | None,
    room: str | None = None,
    patient: Id | None = None,
) -> None:
    scene.rows_before = len(world.booking_appointments.rows)
    try:
        scene.appointment = world.app.book_appointment_as_caller.execute(
            actor_id=actor(scene),
            patient_id=patient or scene.patient,
            appointment_type_id=scene.type,
            start=at(start),
            room_id=scene.rooms[room] if room else None,
            clinician_id=scene.clinicians[clinician] if clinician else None,
        )
    except DomainError as error:
        scene.error = error


@when(parsers.parse('the admin applies "{action}" to it'))
def admin_applies(world: FakeWorld, scene: Scene, action: str) -> None:
    use_case = getattr(world.app, _STATUS_USE_CASES[action])
    change(
        world,
        scene,
        lambda: use_case.execute(actor_id=actor(scene), appointment_id=mine(scene).id),
    )


@when(parsers.parse('the admin applies "{action}" to an unknown appointment'))
def admin_applies_unknown(world: FakeWorld, scene: Scene, action: str) -> None:
    use_case = getattr(world.app, _STATUS_USE_CASES[action])
    change(world, scene, lambda: use_case.execute(actor_id=actor(scene), appointment_id=Id()))


@when(parsers.parse('the admin cancels it giving the reason "{reason}"'))
def admin_cancels(world: FakeWorld, scene: Scene, reason: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.cancel_appointment.execute(
            appointment_id=mine(scene).id, actor_id=actor(scene), reason=reason
        ),
    )


@when(parsers.parse('the admin moves it to "{start}"'))
def admin_moves(world: FakeWorld, scene: Scene, start: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.reschedule_appointment.execute(
            appointment_id=mine(scene).id, actor_id=actor(scene), start=at(start)
        ),
    )


@when(parsers.parse('the admin writes the notes "{text}"'))
def admin_writes_notes(world: FakeWorld, scene: Scene, text: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.write_clinical_notes.execute(
            actor_id=actor(scene), appointment_id=mine(scene).id, text=text
        ),
    )


@when(parsers.re(r'the admin books the patient at "(?P<start>[^"]+)" with "(?P<name>[^"]+)"$'))
def admin_books_with(world: FakeWorld, scene: Scene, start: str, name: str) -> None:
    admin_books(world, scene, start, clinician=name)


@when(parsers.parse('the admin books the patient at "{start}" with "{name}" in room "{room}"'))
def admin_books_in_room(world: FakeWorld, scene: Scene, start: str, name: str, room: str) -> None:
    admin_books(world, scene, start, clinician=name, room=room)


@when(parsers.parse('the admin books the patient at "{start}" without naming a clinician'))
def admin_books_no_clinician(world: FakeWorld, scene: Scene, start: str) -> None:
    admin_books(world, scene, start, clinician=None)


@when(parsers.parse('the admin books "{email}" at "{start}" with "{name}"'))
def admin_books_someone(world: FakeWorld, scene: Scene, email: str, start: str, name: str) -> None:
    admin_books(world, scene, start, clinician=name, patient=scene.people[email])


@when("the admin opens the appointment")
def admin_opens_file(world: FakeWorld, scene: Scene) -> None:
    scene.view = world.app.clinician_appointment.execute(
        actor_id=actor(scene), appointment_id=mine(scene).id
    )


@then(parsers.parse('the file shows no notes and offers "{actions}"'))
def file_without_notes(scene: Scene, actions: str) -> None:
    entry = scene.view.entry
    assert entry.appointment.clinical_notes is None
    assert {a.value for a in entry.actions} == set(csv(actions))


@then(
    parsers.parse(
        'the audit records the change from "{old}" to "{new}" by the admin, with no personal data'
    )
)
def status_audited_by_admin(world: FakeWorld, scene: Scene, old: str, new: str) -> None:
    entries = [e for e in world.audit.entries if e.action == "booking.appointment_status_changed"]
    assert [(e.actor, e.entity_id, dict(e.metadata)) for e in entries] == [
        (actor(scene), mine(scene).id, {"from": old, "to": new})
    ]


@then(parsers.parse('the audit entry "{action}" has the admin as actor and holds only "{keys}"'))
def audited_by_admin(world: FakeWorld, scene: Scene, action: str, keys: str) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert [e.actor for e in entries] == [actor(scene)]
    assert sorted(dict(entries[0].metadata)) == csv(keys)
