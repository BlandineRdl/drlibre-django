"""Steps setting up departments, clinicians, patients and appointments."""

import inspect
from datetime import timedelta

from pytest_bdd import given, parsers, then, when

from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import (
    bookable_type,
    existing_appointment,
    patient_user,
)
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import (
    Scene,
    add_clinician,
    amend_clinician,
    amend_type,
    at,
    book,
    booked,
    csv,
)


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


@when(parsers.re(r'the patient books "(?P<name>[^"]+)" at "(?P<start>[^"]+)"$'))
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


def book_as_caller(
    world: FakeWorld, scene: Scene, name: str, start: str, *, patient: Id, room: Id | None
) -> None:
    scene.rows_before = len(world.booking_appointments.rows)
    try:
        scene.appointment = world.app.book_appointment_as_caller.execute(
            actor_id=scene.patient,
            appointment_type_id=scene.type,
            start=at(start),
            clinician_id=scene.clinicians[name],
            patient_id=patient,
            room_id=room,
        )
    except DomainError as error:
        scene.error = error


@when(parsers.parse('the patient books "{name}" at "{start}" naming themself'))
def patient_books_naming_self(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    book_as_caller(world, scene, name, start, patient=scene.patient, room=None)


@when(parsers.parse('the patient books "{name}" at "{start}" naming another patient'))
def patient_books_other(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    book_as_caller(world, scene, name, start, patient=Id(), room=None)


@when(parsers.parse('the patient books "{name}" at "{start}" in room "{room}"'))
def patient_books_room(world: FakeWorld, scene: Scene, name: str, start: str, room: str) -> None:
    book_as_caller(world, scene, name, start, patient=scene.patient, room=scene.rooms[room])
