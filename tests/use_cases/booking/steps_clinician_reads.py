"""Steps of a clinician reading their day, week, appointment file, patients and rooms."""

import dataclasses
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from pytest_bdd import given, parsers, then, when

from drlibre.audit.application.ports.outbound import AuditEntry
from drlibre.booking.application.ports.inbound import ClinicianEntry, ClinicianFilter
from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.scheduling.application.ports.outbound import StoredSlot
from drlibre.scheduling.domain.slot import Slot
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.builders_booking import existing_appointment, patient_user
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_clinician import caller
from tests.use_cases.booking.support import VISIT_REASON, Scene, at, csv, mine

HALF_HOUR = timedelta(minutes=30)


def read(scene: Scene, call: Callable[[], Any]) -> None:
    try:
        scene.view = call()
    except DomainError as error:
        scene.error = error


def view(scene: Scene) -> Any:
    assert scene.view is not None, scene.error
    return scene.view


def day_entries(scene: Scene) -> list[ClinicianEntry]:
    return [entry for hour in view(scene).hours for entry in hour.entries]


@given(parsers.parse('the agenda names the type "{name}" coloured "{colour}" and each room'))
def agenda_labels(world: FakeWorld, scene: Scene, name: str, colour: str) -> None:
    labels = world.clinician_agenda.labels
    labels[scene.type] = name
    labels.update({room_id: room for room, room_id in scene.rooms.items()})
    world.clinician_agenda.colours[scene.type] = colour


@given(parsers.parse('a patient "{name}"'))
def named_patient(world: FakeWorld, scene: Scene, name: str) -> None:
    patient_id = Id()
    user = patient_user(patient_id, email=f"{patient_id}@example.org")
    world.users.save(dataclasses.replace(user, full_name=name))
    scene.named[name] = patient_id


@given(
    parsers.parse(
        '"{who}" has a "{status}" appointment with "{name}" at "{start}" in room "{room}"'
    )
)
def named_appointment(
    world: FakeWorld, scene: Scene, who: str, status: str, name: str, start: str, room: str
) -> None:
    world.booking_appointments.rows.append(
        existing_appointment(
            patient_id=scene.named[who],
            clinician_id=scene.clinicians[name],
            appointment_type_id=scene.type,
            start=at(start),
            end=at(start) + HALF_HOUR,
            room_id=scene.rooms[room],
            status=AppointmentStatus(status),
            reason=VISIT_REASON,
        )
    )


@given(parsers.parse('"{name}" has a stored free slot at "{start}"'))
def stored_free_slot(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    slot = Slot(at(start), at(start) + HALF_HOUR)
    world.slots.rows.append(StoredSlot(scene.clinicians[name], scene.type, slot))


@given(parsers.parse('a visitor holds the slot of "{name}" at "{start}"'))
def visitor_holds(world: FakeWorld, scene: Scene, name: str, start: str) -> None:
    details = VisitorDetails(
        full_name="Ana Martin",
        birth_date=date(1990, 5, 17),
        email="ana@example.org",
        phone=None,
        reason=None,
    )
    hold = BookingHold.open(
        clinician_id=scene.clinicians[name],
        appointment_type_id=scene.type,
        start=at(start),
        duration=HALF_HOUR,
        source=Source.ONLINE,
        details=details,
        at=world.clock.now(),
    )
    world.holds.add(hold)


@given(parsers.parse('the audit holds "{action}" on the appointment by the {who} at "{when_}"'))
def audited_on_appointment(
    world: FakeWorld, scene: Scene, action: str, who: str, when_: str
) -> None:
    actors = {"patient": scene.patient, "clinician": caller(scene), "staff": Id()}
    world.audit.record(
        AuditEntry.from_event(
            actor=actors[who],
            action=action,
            entity_type="appointment",
            entity_id=mine(scene).id,
            at=at(when_),
        )
    )


@when("the clinician opens their day")
def opens_today(world: FakeWorld, scene: Scene) -> None:
    read(scene, lambda: world.app.clinician_day.execute(actor_id=caller(scene), day=None))


@when(parsers.parse('the clinician opens the day "{day}"'))
def opens_day(world: FakeWorld, scene: Scene, day: str) -> None:
    asked = date.fromisoformat(day)
    read(scene, lambda: world.app.clinician_day.execute(actor_id=caller(scene), day=asked))


@when(parsers.parse('the clinician opens the week of "{day}"'))
def opens_week(world: FakeWorld, scene: Scene, day: str) -> None:
    asked = date.fromisoformat(day)
    read(scene, lambda: world.app.clinician_week.execute(actor_id=caller(scene), week=asked))


@when("the clinician opens the appointment")
def opens_file(world: FakeWorld, scene: Scene) -> None:
    read(
        scene,
        lambda: world.app.clinician_appointment.execute(
            actor_id=caller(scene), appointment_id=mine(scene).id
        ),
    )


@when("the clinician opens an unknown appointment")
def opens_unknown_file(world: FakeWorld, scene: Scene) -> None:
    read(
        scene,
        lambda: world.app.clinician_appointment.execute(
            actor_id=caller(scene), appointment_id=Id()
        ),
    )


@when(parsers.re(r'the clinician lists their patients(?: searching "(?P<text>[^"]*)")?$'))
def lists_patients(world: FakeWorld, scene: Scene, text: str | None) -> None:
    request = PageRequest(search=text or "")
    read(
        scene, lambda: world.app.clinician_patients.execute(actor_id=caller(scene), request=request)
    )


@when(parsers.parse('the clinician opens the rooms of the day "{day}"'))
def opens_rooms(world: FakeWorld, scene: Scene, day: str) -> None:
    asked = date.fromisoformat(day)
    read(
        scene,
        lambda: world.app.department_rooms_day.execute(actor_id=caller(scene), day=asked),
    )


@when("the clinician lists their appointments")
def lists_appointments(world: FakeWorld, scene: Scene) -> None:
    read(
        scene,
        lambda: world.app.list_clinician_appointments.execute(
            actor_id=caller(scene), agenda_filter=ClinicianFilter()
        ),
    )


@then(parsers.parse('the reading is refused as "{code}"'))
def reading_refused(scene: Scene, code: str) -> None:
    assert scene.view is None
    assert scene.error is not None
    assert scene.error.code.value == code


@then(parsers.parse('the day shown is "{day}" in the zone "{zone}"'))
def day_shown(scene: Scene, day: str, zone: str) -> None:
    assert (view(scene).day, view(scene).time_zone) == (date.fromisoformat(day), zone)


@then(parsers.parse('the day lists the appointments at "{starts}"'))
def day_lists(scene: Scene, starts: str) -> None:
    assert [e.appointment.start for e in day_entries(scene)] == [at(s) for s in csv(starts)]


@then(parsers.parse('the day groups them under the hours "{hours}"'))
def day_hours(scene: Scene, hours: str) -> None:
    assert [h.hour for h in view(scene).hours] == [int(h) for h in csv(hours)]


@then(parsers.parse('the hour {hour:d} shows "{who}" for "{kind}" in room "{room}" as "{status}"'))
def hour_shows(scene: Scene, hour: int, who: str, kind: str, room: str, status: str) -> None:
    (group,) = [h for h in view(scene).hours if h.hour == hour]
    shown = [
        (e.patient_name, e.appointment_type, e.room, e.appointment.status) for e in group.entries
    ]
    assert (who, kind, room, AppointmentStatus(status)) in shown


@then(
    parsers.parse(
        "the day counts {booked:d} appointments, {cancelled:d} cancelled,"
        " {completed:d} completed and {absent:d} absent"
    )
)
def day_counts(scene: Scene, booked: int, cancelled: int, completed: int, absent: int) -> None:
    counts = view(scene).counts
    assert (counts.appointments, counts.cancelled, counts.completed, counts.no_show) == (
        booked,
        cancelled,
        completed,
        absent,
    )


@then(parsers.parse('the next free slot is "{start}"'))
def next_free(scene: Scene, start: str) -> None:
    assert view(scene).next_free_slot == at(start)


@then("there is no next free slot")
def no_next_free(scene: Scene) -> None:
    assert view(scene).next_free_slot is None


@then(parsers.parse('every shown appointment is with "{name}"'))
def all_with(scene: Scene, name: str) -> None:
    shown = view(scene)
    entries = shown if isinstance(shown, tuple) else getattr(shown, "entries", None)
    entries = day_entries(scene) if entries is None else entries
    assert entries
    assert {e.appointment.clinician_id for e in entries} == {scene.clinicians[name]}


@then("no listed appointment carries its notes")
def listed_without_notes(scene: Scene) -> None:
    assert [e.appointment.clinical_notes for e in view(scene)] == [None] * len(view(scene))


@then(parsers.parse('the week starts on "{day}" in the zone "{zone}"'))
def week_starts(scene: Scene, day: str, zone: str) -> None:
    assert (view(scene).monday, view(scene).time_zone) == (date.fromisoformat(day), zone)


@then(parsers.parse('the week shows the appointments at "{starts}" coloured "{colour}"'))
def week_shows(scene: Scene, starts: str, colour: str) -> None:
    entries = view(scene).entries
    assert [e.appointment.start for e in entries] == [at(s) for s in csv(starts)]
    assert {e.type_colour for e in entries} == {colour}


@then(
    parsers.parse(
        'the file shows "{who}", phone "{phone}", age {age:d}, "{kind}" in room "{room}",'
        ' the reason and the status "{status}"'
    )
)
def file_shows(
    scene: Scene, who: str, phone: str, age: int, kind: str, room: str, status: str
) -> None:
    file = view(scene)
    entry = file.entry
    assert (
        entry.patient_name,
        entry.patient_phone,
        file.patient_age,
        entry.appointment_type,
        entry.room,
        entry.appointment.reason,
        entry.appointment.status,
        entry.appointment.start,
    ) == (who, phone, age, kind, room, VISIT_REASON, AppointmentStatus(status), mine(scene).start)


@then(parsers.parse('the file shows the notes "{text}" and offers "{actions}"'))
def file_notes_and_actions(scene: Scene, text: str, actions: str) -> None:
    entry = view(scene).entry
    assert entry.appointment.clinical_notes == text
    assert {a.value for a in entry.actions} == set(csv(actions))


@then(parsers.parse('the history lists "{lines}"'))
def history_lists(scene: Scene, lines: str) -> None:
    shown = [f"{h.action} by {h.actor.value}" for h in view(scene).history]
    assert shown == [line.strip() for line in lines.split(";")]


@then(parsers.parse('the patients shown are "{names}"'))
def patients_shown(scene: Scene, names: str) -> None:
    assert [p.full_name for p in view(scene).items] == csv(names)


@then(
    parsers.parse(
        '"{who}" shows the phone "{phone}", last visit "{last}" and next visit "{following}"'
    )
)
def patient_dates(scene: Scene, who: str, phone: str, last: str, following: str) -> None:
    (found,) = [p for p in view(scene).items if p.full_name == who]
    expected = (
        phone,
        None if last == "none" else at(last),
        None if following == "none" else at(following),
    )
    assert (found.phone, found.last_visit, found.next_visit) == expected


@then(parsers.parse('the rooms shown are "{names}" on "{day}" in the zone "{zone}"'))
def rooms_shown(scene: Scene, names: str, day: str, zone: str) -> None:
    shown = view(scene)
    assert [r.name for r in shown.rooms] == csv(names)
    assert (shown.day, shown.time_zone) == (date.fromisoformat(day), zone)


@then(parsers.parse('room "{room}" is taken at "{start}" by "{label}"'))
def room_taken(scene: Scene, room: str, start: str, label: str) -> None:
    taken = [
        (b.patient_name or "Occupied")
        for b in view(scene).bookings
        if b.room_id == scene.rooms[room] and b.start == at(start)
    ]
    assert taken == [label]


@then(parsers.parse('the rooms are taken only at "{starts}"'))
def rooms_taken_only(scene: Scene, starts: str) -> None:
    assert [b.start for b in view(scene).bookings] == [at(s) for s in csv(starts)]
