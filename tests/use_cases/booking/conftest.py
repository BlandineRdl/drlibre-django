import dataclasses
import inspect
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import bookable_clinician, bookable_type, existing_appointment
from tests.fakes.world import FakeWorld


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
    world.patients.active.add(scene.patient)


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
            status=AppointmentStatus.CONFIRMED,
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
    assert world.notices.confirmations == []
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
    assert world.notices.confirmations == [booked(scene)]


@then("the booking offers no way to name an end time")
def no_end_time() -> None:
    assert "end" not in inspect.signature(FakeWorld().app.book_appointment.execute).parameters


@then("the booking offers no way to name a patient or a room")
def no_other_patient_or_room() -> None:
    names = set(inspect.signature(FakeWorld().app.book_appointment.execute).parameters)
    assert names == {"patient_id", "appointment_type_id", "clinician_id", "start"}
