"""Steps of a clinician acting on their own appointments."""

import dataclasses
from datetime import datetime, timedelta

from pytest_bdd import given, parsers, then, when

from drlibre.booking.application.ports.inbound import AgendaFilter
from drlibre.booking.domain.booking_rules import clinician_actions
from drlibre.scheduling.application.ports.outbound import AppointmentType, Clinician, StoredSlot
from drlibre.scheduling.domain.slot import Slot
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import patient_user
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_changes import change
from tests.use_cases.booking.support import Scene, at, booked, csv, mine

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


def book_for_patient(
    world: FakeWorld,
    scene: Scene,
    start: str,
    *,
    clinician: str | None = None,
    room: str | None = None,
) -> None:
    scene.rows_before = len(world.booking_appointments.rows)
    try:
        scene.appointment = world.app.book_for_patient.execute(
            actor_id=caller(scene),
            patient_id=scene.patient,
            appointment_type_id=scene.type,
            start=at(start),
            room_id=scene.rooms[room] if room else None,
            clinician_id=scene.clinicians[clinician] if clinician else None,
        )
    except DomainError as error:
        scene.error = error


def week_strip(world: FakeWorld, scene: Scene, name: str, *, for_patient: bool) -> set[datetime]:
    week = world.app.find_free_week.execute(
        appointment_type_id=scene.type,
        clinician_id=scene.clinicians[name],
        week=None,
        for_patient=for_patient,
    )
    return {slot.start for slot in week.slots}


@given("the patient account is inactive")
def inactive_patient(world: FakeWorld, scene: Scene) -> None:
    world.users.save(patient_user(scene.patient, active=False))


@given(parsers.parse('an inactive room "{room}" in that department'))
def inactive_room(scene: Scene, room: str) -> None:
    # The directory lists active rooms only, so this one stays out of it.
    scene.rooms[room] = Id()


@given(parsers.parse('"{name}" has a free slot in the week strip at "{start}"'))
def week_strip_slot(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    clinician_id = scene.clinicians[name]
    world.scheduling_directory.types[scene.type] = AppointmentType(
        scene.type, scene.department, 30, 0, active=True, time_zone="Europe/Paris"
    )
    world.scheduling_directory.clinicians[clinician_id] = Clinician(
        clinician_id, scene.department, "Europe/Paris", active=True
    )
    slot = Slot(at(start), at(start) + timedelta(minutes=30))
    world.slots.rows.append(StoredSlot(clinician_id, scene.type, slot))


@when(parsers.parse('the clinician cancels it giving the reason "{reason}"'))
def clinician_cancels(world: FakeWorld, scene: Scene, reason: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.cancel_appointment.execute(
            appointment_id=mine(scene).id, actor_id=caller(scene), reason=reason
        ),
    )


@when(parsers.parse('the clinician moves it to "{start}"'))
def clinician_moves(world: FakeWorld, scene: Scene, start: str) -> None:
    change(
        world,
        scene,
        lambda: world.app.reschedule_appointment.execute(
            appointment_id=mine(scene).id, actor_id=caller(scene), start=at(start)
        ),
    )


@when(parsers.re(r'the clinician books the patient at "(?P<start>[^"]+)"$'))
def clinician_books(world: FakeWorld, scene: Scene, start: str) -> None:
    book_for_patient(world, scene, start)


@when(parsers.parse('the clinician books the patient at "{start}" with "{name}"'))
def clinician_books_naming(world: FakeWorld, scene: Scene, start: str, name: str) -> None:
    book_for_patient(world, scene, start, clinician=name)


@when(parsers.parse('the clinician books the patient at "{start}" in room "{room}"'))
def clinician_books_in_room(world: FakeWorld, scene: Scene, start: str, room: str) -> None:
    book_for_patient(world, scene, start, room=room)


@then("the notification names neither the patient nor the reason")
def notification_without_name_or_reason(world: FakeWorld, scene: Scene) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None
    assert stored.cancellation_reason is not None
    (notification,) = world.notifications.rows
    shown = f"{notification.title} {notification.body}"
    assert stored.cancellation_reason not in shown
    assert world.users.rows[scene.patient].full_name not in shown


@then(parsers.parse('the clinician\'s week strip of "{name}" offers "{start}"'))
def clinician_strip_offers(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    assert at(start) in week_strip(world, scene, name, for_patient=False)


@then(parsers.parse('the patient\'s week strip of "{name}" does not offer "{start}"'))
def patient_strip_hides(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    assert at(start) not in week_strip(world, scene, name, for_patient=True)


@then(parsers.parse('the appointment keeps its clinician "{name}" and its type'))
def keeps_clinician_and_type(world: FakeWorld, scene: Scene, name: str) -> None:
    stored = world.booking_appointments.get(mine(scene).id)
    assert stored is not None, scene.error
    assert stored.start != mine(scene).start
    assert (stored.clinician_id, stored.appointment_type_id) == (scene.clinicians[name], scene.type)


@then(parsers.parse('the patient has one "{title}" notification about the booking'))
def notified_of_booking(world: FakeWorld, scene: Scene, title: str) -> None:
    appointment = booked(scene)
    rows = [n for n in world.notifications.rows if n.recipient_id == scene.patient]
    assert [(n.title, n.appointment_id) for n in rows] == [(title, appointment.id)]


@then(
    parsers.parse('the audit entry "{action}" has the clinician as actor and holds only "{keys}"')
)
def audited_by_clinician(world: FakeWorld, scene: Scene, action: str, keys: str) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert [e.actor for e in entries] == [caller(scene)]
    assert sorted(dict(entries[0].metadata)) == csv(keys)
