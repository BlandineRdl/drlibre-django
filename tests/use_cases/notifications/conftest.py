from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from drlibre.booking.domain.appointment import Appointment
from drlibre.notifications.domain.notification import AppointmentEvent, Notification
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.builders_booking import bookable_clinician, bookable_type, booking_venue, patient_user
from tests.fakes.world import FakeWorld

PROVIDER = "Dr Alice Durand"
VISITOR: dict[str, Any] = {
    "full_name": "Léa Martin",
    "birth_date": "1990-05-17",
    "email": "lea@example.org",
    "phone": "0601020304",
    "accepted_terms": True,
}


class Scene:
    def __init__(self) -> None:
        self.patient = Id()
        self.other_patient = Id()
        self.clinician = Id()
        self.type = Id()
        self.appointment: Appointment | None = None
        self.error: Exception | None = None
        self.reason = ""
        self.seeded: dict[datetime, Notification] = {}
        self.other: Notification | None = None
        self.listed: tuple[Notification, ...] = ()
        self.marked: Notification | None = None


@pytest.fixture
def scene() -> Scene:
    return Scene()


def at(raw: str) -> datetime:
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def seed(world: FakeWorld, recipient: Id, created: datetime) -> Notification:
    notification = Notification.for_event(
        event=AppointmentEvent.BOOKED,
        recipient_id=recipient,
        appointment_id=Id(),
        start=at("2026-11-25 13:30"),
        zone_name="Europe/Paris",
        at=created,
    )
    world.notifications.add(notification)
    return notification


def only_notification(world: FakeWorld) -> Notification:
    (notification,) = world.notifications.rows
    return notification


def mark(world: FakeWorld, scene: Scene, notification_id: Id) -> None:
    try:
        scene.marked = world.app.mark_notification_read.execute(
            user_id=scene.patient, notification_id=notification_id
        )
    except DomainError as error:
        scene.error = error


@given("a signed-in patient")
def patient(world: FakeWorld, scene: Scene) -> None:
    world.users.save(patient_user(scene.patient))


@given(parsers.parse('a clinician free at "{start}" seen in "{zone}"'))
def free_clinician(world: FakeWorld, scene: Scene, start: str, zone: str) -> None:
    department = Id()
    kind = bookable_type(department, needs_room=False)
    clinician = bookable_clinician(department)
    scene.type, scene.clinician = kind.id, clinician.id
    world.booking_directory.types[kind.id] = kind
    world.booking_directory.clinicians[clinician.id] = clinician
    venue = booking_venue(PROVIDER)
    assert venue.time_zone == zone
    world.booking_directory.venues[clinician.id] = venue
    world.free_slots.free.add((clinician.id, kind.id, at(start)))


@given("the audit log is unavailable")
def audit_unavailable(world: FakeWorld) -> None:
    world.audit.failing = True


@given(parsers.parse('the patient has notifications created at "{moments}"'))
def own_notifications(world: FakeWorld, scene: Scene, moments: str) -> None:
    for raw in moments.split(","):
        created = at(raw.strip())
        scene.seeded[created] = seed(world, scene.patient, created)


@given(parsers.parse('another patient has a notification created at "{moment}"'))
def other_notification(world: FakeWorld, scene: Scene, moment: str) -> None:
    scene.other = seed(world, scene.other_patient, at(moment))


@when(parsers.parse('the patient books that clinician at "{start}"'))
def patient_books(world: FakeWorld, scene: Scene, start: str) -> None:
    try:
        scene.appointment = world.app.book_appointment.execute(
            patient_id=scene.patient,
            appointment_type_id=scene.type,
            clinician_id=scene.clinician,
            start=at(start),
        )
    except Exception as error:
        scene.error = error


@when(parsers.parse('a visitor books that clinician at "{start}" with the reason "{reason}"'))
def visitor_books(world: FakeWorld, scene: Scene, start: str, reason: str) -> None:
    scene.reason = reason
    hold = world.app.create_hold.execute(
        appointment_type_id=scene.type,
        clinician_id=scene.clinician,
        start=at(start),
        network="10.0.0.1",
        reason=reason,
        **VISITOR,
    )
    world.app.verify_hold.execute(hold_id=hold.hold_id, code="123456", user_agent="pytest")


@when("the patient lists their notifications")
def lists(world: FakeWorld, scene: Scene) -> None:
    page = world.app.list_notifications.execute(recipient_id=scene.patient, request=PageRequest())
    scene.listed = page.items


@given("an hour passes")
def hour_passes(world: FakeWorld) -> None:
    world.clock.at += timedelta(hours=1)


@given(parsers.parse('the patient marked the notification created at "{moment}" read'))
@when(parsers.parse('the patient marks the notification created at "{moment}" read'))
def marks_own(world: FakeWorld, scene: Scene, moment: str) -> None:
    mark(world, scene, scene.seeded[at(moment)].id)


@when("the patient marks that other notification read")
def marks_other(world: FakeWorld, scene: Scene) -> None:
    assert scene.other is not None
    mark(world, scene, scene.other.id)


@when("the patient marks an unknown notification read")
def marks_unknown(world: FakeWorld, scene: Scene) -> None:
    mark(world, scene, Id())


@then(
    parsers.parse(
        'the patient has one notification "{title}" of kind "{kind}" for that appointment'
    )
)
def one_notification(world: FakeWorld, scene: Scene, title: str, kind: str) -> None:
    assert scene.appointment is not None, scene.error
    notification = only_notification(world)
    assert notification.recipient_id == scene.patient
    assert notification.title == title
    assert notification.kind.value == kind
    assert notification.appointment_id == scene.appointment.id
    assert not notification.is_read


@then("the only email queued is the confirmation")
def only_confirmation(world: FakeWorld) -> None:
    subjects = [message.subject for message in world.outbox.queued]
    assert subjects == ["Confirmation de votre rendez-vous"]


@then("no appointment, notification or email remains")
def nothing_remains(world: FakeWorld) -> None:
    assert world.booking_appointments.rows == []
    assert world.notifications.rows == []
    assert world.outbox.queued == []


@then(parsers.parse('the booking is refused as "{code}"'))
def refused(scene: Scene, code: str) -> None:
    assert isinstance(scene.error, DomainError)
    assert scene.error.code.value == code


@then(parsers.parse('the notification reads "{body}"'))
def reads(world: FakeWorld, body: str) -> None:
    assert only_notification(world).body == body


@then("the notification names neither the provider, the visitor, the reason nor the email")
def no_personal_data(world: FakeWorld, scene: Scene) -> None:
    notification = only_notification(world)
    text = f"{notification.title} {notification.body}"
    for word in (*PROVIDER.split(), *VISITOR["full_name"].split(), scene.reason):
        assert word not in text
    assert VISITOR["email"] not in text
    assert "@" not in text


@then(parsers.parse('they see the notifications created at "{moments}"'))
def sees(scene: Scene, moments: str) -> None:
    expected = [at(raw.strip()) for raw in moments.split(",")]
    assert [notification.created_at for notification in scene.listed] == expected


@then(parsers.parse('that notification is read at "{moment}"'))
def read_at(world: FakeWorld, scene: Scene, moment: str) -> None:
    assert scene.marked is not None, scene.error
    assert world.notifications.get(scene.marked.id) == scene.marked
    assert scene.marked.read_at == at(moment)


@then(parsers.parse("the patient has {count:d} unread notification"))
def unread(world: FakeWorld, scene: Scene, count: int) -> None:
    assert world.app.count_unread.execute(recipient_id=scene.patient) == count


@then(parsers.parse('the audit holds "{action}" naming only the notification and its kind'))
def audited(world: FakeWorld, scene: Scene, action: str) -> None:
    assert scene.marked is not None
    (entry,) = world.audit.entries
    assert entry.action == action
    assert entry.actor == scene.patient
    assert entry.entity_id == scene.marked.id
    assert entry.metadata == (("kind", "SCHEDULE_CHANGED"),)


@then(parsers.parse('the marking is refused as "{code}"'))
def marking_refused(scene: Scene, code: str) -> None:
    assert isinstance(scene.error, DomainError)
    assert scene.error.code.value == code


@then("the other notification is still unread and nothing was audited")
def other_unread(world: FakeWorld, scene: Scene) -> None:
    assert scene.other is not None
    stored = world.notifications.get(scene.other.id)
    assert stored is not None
    assert not stored.is_read
    assert world.audit.entries == []
