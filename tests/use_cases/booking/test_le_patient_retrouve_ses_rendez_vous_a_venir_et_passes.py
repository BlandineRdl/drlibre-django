import dataclasses
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.booking.application.ports.inbound import AgendaFilter, PatientAppointments
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.session import Session
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, patient_user
from tests.fakes.booking import AgendaClinician
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.conftest import VISIT_REASON, Scene, at, csv, typed_patient, verified

scenarios("../../features/booking/le_patient_retrouve_ses_rendez_vous_a_venir_et_passes.feature")

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


class Listing:
    def __init__(self) -> None:
        self.found: PatientAppointments | None = None
        self.body: dict[str, Any] = {}
        self.other = Id()


@pytest.fixture
def listing() -> Listing:
    return Listing()


@pytest.fixture
def web(world: FakeWorld) -> Iterator[Client]:
    """A browser stand-in served by the real API over the fake wiring."""
    use_container(world.app)
    yield Client()
    use_container(None)


def starts(raw: str) -> list[str]:
    return [] if raw == "none" else csv(raw)


def shown(start: str) -> str:
    return at(start).isoformat()


def open_session(world: FakeWorld, web: Client, patient_id: Id) -> None:
    token = f"token-{patient_id}"
    user = world.users.rows[patient_id]
    world.sessions.add(
        Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent="test", at=world.clock.now()
        )
    )
    web.cookies[COOKIE] = token


@given("the agenda names the clinicians, the type and the rooms")
def agenda_names(world: FakeWorld, scene: Scene) -> None:
    for name, clinician_id in scene.clinicians.items():
        world.agenda.clinicians[clinician_id] = clinician_named(name)
    world.agenda.labels[scene.type] = TYPE_NAME
    world.agenda.labels.update({room_id: name for name, room_id in scene.rooms.items()})


@given(
    parsers.parse('the patient has a "{status}" appointment with "{name}" at "{start}" in no room')
)
def my_roomless_appointment(
    world: FakeWorld, scene: Scene, status: str, name: str, start: str
) -> None:
    scene.mine = existing_appointment(
        patient_id=scene.patient,
        clinician_id=scene.clinicians[name],
        appointment_type_id=scene.type,
        start=at(start),
        end=at(start) + timedelta(minutes=30),
        status=AppointmentStatus(status),
        reason=VISIT_REASON,
    )
    world.booking_appointments.rows.append(scene.mine)


@given(parsers.parse('another patient has a "{status}" appointment with "{name}" at "{start}"'))
def someone_elses_appointment(
    world: FakeWorld, scene: Scene, listing: Listing, status: str, name: str, start: str
) -> None:
    world.users.save(patient_user(listing.other, email="autre@example.org"))
    world.booking_appointments.rows.append(
        existing_appointment(
            patient_id=listing.other,
            clinician_id=scene.clinicians[name],
            appointment_type_id=scene.type,
            start=at(start),
            end=at(start) + timedelta(minutes=30),
            status=AppointmentStatus(status),
        )
    )


@when("the patient lists their appointments")
def lists(world: FakeWorld, scene: Scene, listing: Listing) -> None:
    listing.found = world.app.list_patient_appointments.execute(
        patient_id=scene.patient, agenda_filter=AgendaFilter()
    )


@when(parsers.parse('the patient asks the API for "{query}"'))
def asks_api(world: FakeWorld, scene: Scene, listing: Listing, web: Client, query: str) -> None:
    open_session(world, web, scene.patient)
    params = {} if query == "none" else dict(pair.split("=", 1) for pair in query.split("&"))
    if "clinician" in params:
        params["clinician"] = str(scene.clinicians[params["clinician"]])
    if "patient" in params:
        params["patient"] = str(listing.other)
    response = web.get("/api/v1/appointments", params)
    assert response.status_code == 200, response.content
    listing.body = response.json()


def found(listing: Listing) -> PatientAppointments:
    assert listing.found is not None
    return listing.found


@then(parsers.parse('the upcoming appointments start at "{raw}"'))
def upcoming_at(listing: Listing, raw: str) -> None:
    assert [e.appointment.start for e in found(listing).upcoming] == [at(s) for s in starts(raw)]


@then(parsers.parse('the past appointments start at "{raw}"'))
def past_at(listing: Listing, raw: str) -> None:
    assert [e.appointment.start for e in found(listing).past] == [at(s) for s in starts(raw)]


@then(parsers.parse('the listed appointment shows every field, in room "{room}"'))
def every_field(scene: Scene, listing: Listing, room: str) -> None:
    assert_every_field(scene, listing, room)


@then("the listed appointment shows every field, in no room")
def every_field_without_room(scene: Scene, listing: Listing) -> None:
    assert_every_field(scene, listing, None)


def assert_every_field(scene: Scene, listing: Listing, room: str | None) -> None:
    (entry,) = found(listing).upcoming
    assert scene.mine is not None
    assert entry.appointment == scene.mine
    expected = dataclasses.asdict(clinician_named("A"))
    assert {
        "name": entry.clinician_name,
        "title": entry.clinician_title,
        "specialty": entry.specialty,
        "hospital_name": entry.hospital_name,
        "hospital_address": entry.hospital_address,
        "time_zone": entry.time_zone,
        "department": entry.department,
    } == expected
    assert (entry.room, entry.appointment_type) == (room, TYPE_NAME)


@then(
    parsers.parse(
        'the API lists the new appointment at "{start}" as upcoming with the opened session'
    )
)
def api_lists_new(world: FakeWorld, scene: Scene, web: Client, start: str) -> None:
    web.cookies[COOKIE] = verified(scene).token
    response = web.get("/api/v1/appointments")
    assert response.status_code == 200, response.content
    body = response.json()
    assert [e["start"] for e in body["upcoming"]] == [shown(start)]
    assert body["past"] == []
    stored = world.booking_appointments.rows[-1]
    assert stored.patient_id == typed_patient(world, scene).id


@then(parsers.parse('the API lists the patient\'s appointments at "{raw}"'))
def api_lists(listing: Listing, raw: str) -> None:
    listed = [e["start"] for e in listing.body["upcoming"] + listing.body["past"]]
    assert listed == [shown(s) for s in starts(raw)]
