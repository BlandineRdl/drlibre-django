"""Steps of a patient cancelling or moving an appointment."""

import dataclasses
import inspect
import re
from collections.abc import Callable
from datetime import timedelta
from zoneinfo import ZoneInfo

from pytest_bdd import given, parsers, then, when

from drlibre.booking.application.ports.inbound import AgendaFilter
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import (
    existing_appointment,
)
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_scene import room_busy
from tests.use_cases.booking.support import (
    VISIT_REASON,
    Scene,
    at,
    csv,
    mine,
)


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
    changes = {
        "booking.appointment_cancelled",
        "booking.appointment_rescheduled",
        "booking.appointment_status_changed",
        "booking.appointment_notes_written",
    }
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
