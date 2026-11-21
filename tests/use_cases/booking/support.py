"""Shared scene, builders and helpers of the booking scenarios."""

import dataclasses
from datetime import UTC, datetime
from typing import Any

from django.conf import settings
from django.test import Client

from drlibre.booking.application.ports.inbound import HoldCreated, VerifiedBooking
from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import User
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import (
    bookable_clinician,
    booking_venue,
)
from tests.fakes.booking import AgendaClinician
from tests.fakes.world import FakeWorld

NETWORK = "10.0.0.1"
VISITOR_FORM: dict[str, Any] = {
    "full_name": "Léa Martin",
    "birth_date": "1990-05-17",
    "email": "lea@example.org",
    "phone": "0601020304",
    "reason": "Douleur au genou",
    "accepted_terms": True,
}


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
        self.form: dict[str, Any] = dict(VISITOR_FORM)
        self.hold: HoldCreated | None = None
        self.holds: list[HoldCreated] = []
        self.verified: VerifiedBooking | None = None
        self.successes = 0
        self.existing: User | None = None
        self.mine: Appointment | None = None
        self.caller: Id | None = None
        self.page: Any = None
        self.actor: Id | None = None
        self.people: dict[str, Id] = {}
        self.freed: dict[str, Appointment] = {}
        self.waitlist_before: dict[Id, WaitlistEntry] = {}


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
    world.booking_directory.venues[clinician.id] = booking_venue(name)


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


def booked(scene: Scene) -> Appointment:
    assert scene.appointment is not None, scene.error
    return scene.appointment


def verified(scene: Scene) -> VerifiedBooking:
    assert scene.verified is not None, scene.error
    return scene.verified


def typed_patient(world: FakeWorld, scene: Scene) -> User:
    found = [u for u in world.users.rows.values() if u.email.value == scene.form["email"]]
    assert len(found) == 1
    return found[0]


VISIT_REASON = "Douleur au genou droit"


def mine(scene: Scene) -> Appointment:
    assert scene.mine is not None
    return scene.mine


COOKIE = settings.SESSION_COOKIE_NAME
TYPE_NAME = "Consultation de suivi"


def clinician_named(name: str) -> AgendaClinician:
    return AgendaClinician(
        name=f"Claire {name}",
        title="Dr",
        specialty="Cardiologie",
        hospital_name="Hôpital du Lamentin",
        hospital_address="1 rue des Alizés, 97232 Le Lamentin",
        time_zone="America/Martinique",
        department="Rythmologie",
    )


def open_session(world: FakeWorld, web: Client, user_id: Id) -> None:
    token = f"token-{user_id}"
    user = world.users.rows[user_id]
    world.sessions.add(
        Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent="test", at=world.clock.now()
        )
    )
    web.cookies[COOKIE] = token


def page_text(scene: Scene) -> str:
    assert scene.page is not None
    return scene.page.content.decode()
