"""Steps of a clinician acting on their own appointments."""

import dataclasses

from pytest_bdd import given, parsers, then, when

from drlibre.booking.application.ports.inbound import AgendaFilter
from drlibre.booking.domain.booking_rules import clinician_actions
from drlibre.shared_kernel.ids import Id
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_changes import change
from tests.use_cases.booking.support import Scene, csv, mine

_STATUS_USE_CASES = {
    "check_in": "check_in_appointment",
    "complete": "complete_appointment",
    "no_show": "mark_no_show",
}


def caller(scene: Scene) -> Id:
    assert scene.caller is not None
    return scene.caller


def stored_notes(world: FakeWorld, scene: Scene) -> str | None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None, scene.error
    return stored.clinical_notes


@given(parsers.parse('the signed-in clinician is "{name}"'))
def signed_in_clinician(world: FakeWorld, scene: Scene, name: str) -> None:
    scene.caller = Id()
    world.booking_directory.profiles_of_users[scene.caller] = scene.clinicians[name]


@given("the signed-in user holds no clinician profile")
def signed_in_without_profile(scene: Scene) -> None:
    scene.caller = Id()


@given(parsers.parse('the appointment holds the notes "{text}"'))
def holds_notes(world: FakeWorld, scene: Scene, text: str) -> None:
    rows = world.booking_appointments.rows
    noted = dataclasses.replace(mine(scene), clinical_notes=text)
    rows[rows.index(mine(scene))] = noted
    scene.mine = noted


@when(parsers.parse('the clinician applies "{action}" to it'))
def applies(world: FakeWorld, scene: Scene, action: str) -> None:
    use_case = getattr(world.app, _STATUS_USE_CASES[action])
    change(
        world,
        scene,
        lambda: use_case.execute(actor_id=caller(scene), appointment_id=mine(scene).id),
    )


@when(parsers.parse('the clinician applies "{action}" to an unknown appointment'))
def applies_unknown(world: FakeWorld, scene: Scene, action: str) -> None:
    use_case = getattr(world.app, _STATUS_USE_CASES[action])
    change(world, scene, lambda: use_case.execute(actor_id=caller(scene), appointment_id=Id()))


@when(parsers.parse('the clinician writes the notes "{text}"'))
def writes_notes(world: FakeWorld, scene: Scene, text: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.write_clinical_notes.execute(
            actor_id=caller(scene), appointment_id=mine(scene).id, text=text
        ),
    )


@when(parsers.parse("the clinician writes notes of {length:d} characters"))
def writes_notes_at_length(world: FakeWorld, scene: Scene, length: int) -> None:
    writes_notes(world, scene, "x" * length)


@then(parsers.parse('the appointment is now "{status}"'))
def now_status(world: FakeWorld, scene: Scene, status: str) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None
    assert stored.status.value == status, scene.error


@then(parsers.parse('the clinician is offered "{actions}"'))
def clinician_offered(scene: Scene, actions: str) -> None:
    expected = set() if actions == "nothing" else set(csv(actions))
    assert {action.value for action in clinician_actions(mine(scene))} == expected


@then("no one was notified")
def no_one_notified(world: FakeWorld) -> None:
    assert world.notifications.rows == []
    assert world.outbox.queued == []


@then(
    parsers.parse(
        'the audit records the change from "{old}" to "{new}" by the clinician,'
        " with no personal data"
    )
)
def status_audited(world: FakeWorld, scene: Scene, old: str, new: str) -> None:
    entries = [e for e in world.audit.entries if e.action == "booking.appointment_status_changed"]
    assert [(e.actor, e.entity_id, dict(e.metadata)) for e in entries] == [
        (caller(scene), mine(scene).id, {"from": old, "to": new})
    ]


@then(parsers.parse('the stored notes are "{text}"'))
def notes_are(world: FakeWorld, scene: Scene, text: str) -> None:
    assert stored_notes(world, scene) == text


@then(parsers.parse("the stored notes hold {length:d} characters"))
def notes_length(world: FakeWorld, scene: Scene, length: int) -> None:
    notes = stored_notes(world, scene)
    assert notes is not None
    assert len(notes) == length


@then("the appointment has no notes")
def no_notes(world: FakeWorld, scene: Scene) -> None:
    assert stored_notes(world, scene) is None


@then("the patient sees the appointment without its notes")
def patient_sees_no_notes(world: FakeWorld, scene: Scene) -> None:
    viewed = world.app.view_appointment.execute(
        appointment_id=mine(scene).id, patient_id=scene.patient
    )
    listed = world.app.list_patient_appointments.execute(
        patient_id=scene.patient, agenda_filter=AgendaFilter()
    )
    seen = [viewed, *(e.appointment for e in listed.upcoming + listed.past)]
    assert [a.clinical_notes for a in seen] == [None, None]


@then(
    parsers.parse('the audit records the written field "{field}" by the clinician, never the text')
)
def notes_audited(world: FakeWorld, scene: Scene, field: str) -> None:
    entries = [e for e in world.audit.entries if e.action == "booking.appointment_notes_written"]
    assert [(e.actor, e.entity_id, dict(e.metadata)) for e in entries] == [
        (caller(scene), mine(scene).id, {"fields": (field,)})
    ]
