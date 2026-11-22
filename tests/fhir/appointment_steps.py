"""Steps of the FHIR `Appointment` scenarios on PostgreSQL, a fixed clock and recorded emails."""

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from string import Template
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
    WaitlistEntryRecord,
)
from drlibre.bootstrap.container import container, use_container
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.mappers.directory import extension_url
from drlibre.interfaces.fhir.slot_id import SlotKey, slot_id
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_session, stored_user
from tests.fhir.conftest import token_for
from tests.fhir.directory_steps import Exchange
from tests.integration.bookable import NOW, Bookable, bookable

PARIS = ZoneInfo("Europe/Paris")
MONDAY = date(2026, 11, 23)
_ABSENT = Id(uuid.UUID("00000000-0000-4000-8000-000000000000"))


@dataclass
class Booking:
    """The bookable scene, its people, the appointments by label and the last FHIR booking asked."""

    world: Bookable
    people: dict[str, User]
    tokens: dict[str, str] = field(default_factory=dict)
    # "first 09:00" names the appointment of "first" at 09:00; "first" alone their latest one.
    labels: dict[str, Id] = field(default_factory=dict)
    asked: dict[str, Any] = field(default_factory=dict)

    def user(self, name: str) -> User:
        return self.people[name]

    def profile(self, name: str) -> Id:
        clinicians = self.world.scene.clinicians
        return {"clinician": clinicians[0].id, "colleague": clinicians[1].id}[name]

    def token(self, name: str) -> str:
        if name not in self.tokens:
            self.tokens[name] = token_for(self.people[name])
        return self.tokens[name]

    def headers(self, name: str) -> dict[str, str]:
        return {} if name == "nobody" else {"Authorization": f"Bearer {self.token(name)}"}

    def label(self, found: str) -> str:
        names = {str(i): label for label, i in self.labels.items() if " " in label}
        return names.get(found, found)

    def values(self) -> dict[str, str]:
        found = {name: str(user.id) for name, user in self.people.items()}
        return found | {"room": str(self.world.scene.room), "type": str(self.world.scene.kind)}


@pytest.fixture
def booking() -> Iterator[Booking]:
    with bookable() as world:
        use_container(world.app())
        yield Booking(world, {})
        use_container(None)


def _at(hhmm: str, day: date = MONDAY) -> datetime:
    return datetime.combine(day, time.fromisoformat(hhmm), tzinfo=PARIS)


def _local(raw: str) -> str:
    return f"{datetime.fromisoformat(raw).astimezone(PARIS):%H:%M}"


@given("a bookable department with two clinicians, one room, two patients and an admin")
def bookable_department(booking: Booking) -> None:
    clinicians = booking.world.scene.clinicians
    users = DjangoUsers()
    booking.people = {
        "first": stored_user(Role.PATIENT),
        "second": stored_user(Role.PATIENT),
        "former": stored_user(Role.PATIENT, active=False),
        "admin": stored_user(Role.ADMIN),
    }
    for name, profile in zip(("clinician", "colleague"), clinicians, strict=True):
        user = users.get(profile.user_id)
        assert user is not None
        booking.people[name] = user


def _book(booking: Booking, patient: str, clinician: str, hhmm: str) -> Id:
    booked = container().book_appointment_as_caller.execute(
        actor_id=booking.user(patient).id,
        appointment_type_id=booking.world.scene.kind,
        start=_at(hhmm),
        clinician_id=booking.profile(clinician),
    )
    booking.labels[f"{patient} {hhmm}"] = booking.labels[patient] = booked.id
    return booked.id


@given(parsers.parse('"{patient}" has booked "{clinician}" at "{hhmm}"'))
def has_booked(booking: Booking, patient: str, clinician: str, hhmm: str) -> None:
    if clinician != "nobody":
        _book(booking, patient, clinician, hhmm)


@given(
    parsers.parse(
        '"{patient}" has booked "{clinician}" at "{hhmm}" with the clinical notes "{notes}"'
    )
)
def has_booked_with_notes(
    booking: Booking, patient: str, clinician: str, hhmm: str, notes: str
) -> None:
    booked = _book(booking, patient, clinician, hhmm)
    AppointmentRecord.objects.filter(id=booked.value).update(clinical_notes=notes)


def _parsed(raw: str) -> dict[str, str]:
    pairs = (item.split("=", 1) for item in raw.split(",") if item.strip())
    return {key.strip(): value.strip() for key, value in pairs}


def _requests(booking: Booking, hhmm: str, raw: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The FHIR resource and the application API body of one booking request."""
    asked, scene = _parsed(raw), booking.world.scene
    kind = _ABSENT if asked.get("type") == "absent" else scene.kind
    start = _at(hhmm)
    coding = {"system": f"{base_url()}/HealthcareService", "code": str(kind)}
    resource: dict[str, Any] = {
        "resourceType": "Appointment",
        "status": asked.get("status", "proposed"),
        "serviceType": [{"coding": [coding]}],
    }
    api: dict[str, Any] = {"type": str(kind), "start": start.isoformat()}
    participants = []
    if "slot" in asked:
        profile = booking.profile(asked["slot"])
        key = SlotKey(profile, kind, start.astimezone(UTC))
        resource["slot"] = [{"reference": f"Slot/{slot_id(key)}"}]
        api["clinician"] = str(profile)
    else:
        resource["start"] = start.isoformat()
    if "practitioner" in asked:
        practitioner = booking.user(asked["practitioner"]).id
        participants.append({"actor": {"reference": f"Practitioner/{practitioner}"}})
        api["clinician"] = str(booking.profile(asked["practitioner"]))
    if "patient" in asked:
        patient = booking.user(asked["patient"]).id
        participants.append({"actor": {"reference": f"Patient/{patient}"}})
        api["patient"] = str(patient)
    if "room" in asked:
        participants.append({"actor": {"reference": f"Location/{scene.room}"}})
        api["room"] = str(scene.room)
    if participants:
        resource["participant"] = participants
    if "end" in asked:
        resource["end"] = api["end"] = _at(asked["end"]).isoformat()
    if "reason" in asked:
        resource["reasonCode"] = [{"text": asked["reason"]}]
        api["reason"] = asked["reason"]
    if "status" in asked:
        api["status"] = asked["status"]
    return resource, api


@when(parsers.re(r'"(?P<who>[^"]+)" books in FHIR at "(?P<hhmm>[^"]+)" with "(?P<raw>[^"]*)"'))
def books_in_fhir(booking: Booking, exchange: Exchange, who: str, hhmm: str, raw: str) -> None:
    resource, api = _requests(booking, hhmm, raw)
    booking.asked = {"who": who, "api": api}
    exchange.response = Client().post(
        "/fhir/Appointment",
        data=json.dumps(resource),
        content_type="application/fhir+json",
        headers=booking.headers(who),
    )
    if exchange.response.status_code == 201:
        patient = _parsed(raw).get("patient", who)
        booking.labels[f"{patient} {hhmm}"] = booking.labels[patient] = Id.parse(
            exchange.body()["id"]
        )


@when(parsers.parse('"{patient}" books "{clinician}" at "{hhmm}" on the booking screen'))
def books_on_screen(booking: Booking, patient: str, clinician: str, hhmm: str) -> None:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(booking.user(patient))
    data = {
        "type": str(booking.world.scene.kind),
        "clinician": str(booking.profile(clinician)),
        "start": _at(hhmm).isoformat(),
    }
    response = client.post("/booking/new", data)
    assert response.status_code == 302, response.content
    booking.labels[patient] = Id.parse(response["Location"].rstrip("/").rpartition("/")[2])


@then("the application API answers the same to the same booking")
def api_answers_the_same(booking: Booking, exchange: Exchange) -> None:
    replayed = Client().post(
        "/api/v1/appointments",
        data=json.dumps(booking.asked["api"]),
        content_type="application/json",
        headers=booking.headers(booking.asked["who"]),
    )
    issue = exchange.body()["issue"][0]
    code = issue["details"]["coding"][0]["code"]
    answer = replayed.json()
    assert (replayed.status_code, answer["code"]) == (exchange.response.status_code, code), answer
    # Field names are FHIR paths on one side, API names on the other; other details match.
    if code != "invalid_input":
        assert json.loads(issue.get("diagnostics", "{}")) == (answer["details"] or {})


def _participants(body: dict[str, Any]) -> list[str]:
    return [p["actor"]["reference"] for p in body.get("participant", [])]


def _source(body: dict[str, Any]) -> list[str]:
    return [
        e["valueCode"] for e in body.get("extension", []) if e["url"] == extension_url("source")
    ]


def _created(exchange: Exchange) -> dict[str, Any]:
    body = exchange.body()
    assert exchange.response.status_code == 201, body
    assert exchange.response["Location"] == f"{base_url()}/Appointment/{body['id']}"
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    return body


@then(
    parsers.parse(
        'the appointment is created "{status}" with "{clinician}", the room, the end at "{end}"'
        ' and the source "{source}"'
    )
)
def created(
    booking: Booking, exchange: Exchange, status: str, clinician: str, end: str, source: str
) -> None:
    body = _created(exchange)
    assert body["status"] == status
    assert f"Practitioner/{booking.user(clinician).id}" in _participants(body)
    assert f"Location/{booking.world.scene.room}" in _participants(body)
    assert _local(body["end"]) == end
    assert _source(body) == [source]


@then(
    parsers.parse(
        'the appointment is created "{status}" with a clinician of the department and the source'
        ' "{source}"'
    )
)
def created_round_robin(booking: Booking, exchange: Exchange, status: str, source: str) -> None:
    body = _created(exchange)
    clinicians = {f"Practitioner/{booking.user(n).id}" for n in ("clinician", "colleague")}
    assert body["status"] == status
    assert clinicians & set(_participants(body))
    assert _source(body) == [source]


@then(
    parsers.parse(
        'the "{first}" and "{second}" bookings leave alike audit entries, the same notification'
        " and the same email"
    )
)
def alike_bookings(booking: Booking, first: str, second: str) -> None:
    def trace(who: str) -> tuple[Any, ...]:
        appointment = booking.labels[who].value
        audit = list(
            AuditEntryRecord.objects.filter(entity_id=appointment).values(
                "action", "entity_type", "metadata"
            )
        )
        notices = list(
            NotificationRecord.objects.filter(appointment_id=appointment).values("kind", "title")
        )
        to = (booking.user(who).email.value,)
        subjects = [m.subject for m in booking.world.outbox.queued if m.to == to]
        return audit, notices, subjects

    found = trace(first)
    assert all(found)
    assert found == trace(second)


@when(parsers.parse('"{who}" reads the appointment of "{owner}"'))
def reads_appointment(booking: Booking, exchange: Exchange, who: str, owner: str) -> None:
    found = _ABSENT if owner == "absent" else booking.labels[owner]
    exchange.response = Client().get(f"/fhir/Appointment/{found}", headers=booking.headers(who))


@when(parsers.re(r'"(?P<who>[^"]+)" searches the appointments with "(?P<query>[^"]*)"'))
def searches_appointments(booking: Booking, exchange: Exchange, who: str, query: str) -> None:
    path = f"/fhir/Appointment?{Template(query).substitute(booking.values())}"
    exchange.response = Client().get(path, headers=booking.headers(who))


def _matches(exchange: Exchange) -> list[dict[str, Any]]:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    if body["resourceType"] == "Appointment":
        return [body]
    return [e["resource"] for e in body.get("entry", []) if e["search"]["mode"] == "match"]


@then(parsers.re(r'the FHIR appointments found are "(?P<labels>[^"]*)"'))
def appointments_found(booking: Booking, exchange: Exchange, labels: str) -> None:
    found = [booking.label(r["id"]) for r in _matches(exchange)]
    assert found == [label.strip() for label in labels.split(",") if label.strip()]


@then(parsers.parse('the bundle includes the "{resource}" "{who}"'))
def bundle_includes(booking: Booking, exchange: Exchange, resource: str, who: str) -> None:
    included = [
        (e["resource"]["resourceType"], e["resource"]["id"])
        for e in exchange.body().get("entry", [])
        if e["search"]["mode"] == "include"
    ]
    assert included == [(resource, booking.values()[who])]


def _appointment(patient: User, profile: Id, start: datetime, status: str, **extra: Any) -> Id:
    record = AppointmentRecord.objects.create(
        patient_id=patient.id.value,
        clinician_id=profile.value,
        appointment_type_id=extra.pop("kind"),
        start=start,
        end=start + timedelta(minutes=30),
        status=status,
        source="ONLINE",
        **extra,
    )
    return Id(record.id)


@given(parsers.parse('"{patient}" has an appointment and a waitlist entry in every status'))
def every_status(booking: Booking, patient: str) -> None:
    scene, owner = booking.world.scene, booking.user(patient)
    profile, kind = booking.profile("clinician"), scene.kind.value
    statuses = ("BOOKED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW")
    for day, status in enumerate(statuses, start=1):
        extra: dict[str, Any] = {"kind": kind, "reason": "Douleur"}
        if status == "CANCELLED":
            extra |= {"cancelled_at": NOW, "cancellation_reason": "Empêchement"}
        booking.labels[status] = _appointment(
            owner, profile, _at("09:00", MONDAY + timedelta(days=day)), status, **extra
        )
    freed = _appointment(
        booking.user("second"),
        profile,
        _at("11:00"),
        "CANCELLED",
        kind=kind,
        cancelled_at=NOW,
        cancellation_reason="Empêchement",
    )
    booking.labels["freed"] = freed
    window = {"earliest": _at("08:00"), "latest": _at("18:00"), "created_at": NOW}
    for status in ("WAITING", "OFFERED", "EXPIRED", "BOOKED"):
        WaitlistEntryRecord.objects.create(
            patient_id=owner.id.value,
            appointment_type_id=kind,
            status=status,
            offered_appointment_id=freed.value if status == "OFFERED" else None,
            **window,
        )


@then(parsers.parse('the FHIR statuses are "{statuses}"'))
def statuses_are(exchange: Exchange, statuses: str) -> None:
    found = sorted(r["status"] for r in _matches(exchange))
    assert found == sorted(s.strip() for s in statuses.split(","))


def _of_status(exchange: Exchange, status: str) -> list[dict[str, Any]]:
    return [r for r in _matches(exchange) if r["status"] == status]


@then(
    parsers.parse(
        'the booked appointment carries only the source extension "{source}" and the reason'
        ' text "{reason}"'
    )
)
def booked_fields(exchange: Exchange, source: str, reason: str) -> None:
    (found,) = _of_status(exchange, "booked")
    assert found["extension"] == [{"url": extension_url("source"), "valueCode": source}]
    assert found["reasonCode"] == [{"text": reason}]
    assert "cancelationReason" not in found


@then(parsers.parse('the cancelled appointment carries its cancellation reason "{reason}"'))
def cancelled_fields(booking: Booking, exchange: Exchange, reason: str) -> None:
    reasons = {r["id"]: r.get("cancelationReason") for r in _of_status(exchange, "cancelled")}
    # The expired waitlist entry is cancelled too, without a reason.
    assert reasons.pop(str(booking.labels["CANCELLED"])) == {"text": reason}
    assert list(reasons.values()) == [None]


@then("the proposed entry shows the offered start and practitioner")
def proposed_fields(booking: Booking, exchange: Exchange) -> None:
    (found,) = _of_status(exchange, "proposed")
    assert _local(found["start"]) == "11:00"
    assert _participants(found) == [
        f"Patient/{booking.user('first').id}",
        f"Practitioner/{booking.user('clinician').id}",
    ]
    assert "Location" not in " ".join(_participants(found))


@then(parsers.parse('the appointment shows the notes "{notes}"'))
def shows_notes(exchange: Exchange, notes: str) -> None:
    assert _matches(exchange)[0]["comment"] == notes


@then("the appointment shows no notes")
def shows_no_notes(exchange: Exchange) -> None:
    assert "comment" not in _matches(exchange)[0]


@given(parsers.parse('a visitor holds "{clinician}" at "{hhmm}" and an older hold has expired'))
def holds(booking: Booking, clinician: str, hhmm: str) -> None:
    def hold(at: str, expires_at: datetime) -> Id:
        record = BookingHoldRecord.objects.create(
            clinician_id=booking.profile(clinician).value,
            appointment_type_id=booking.world.scene.kind.value,
            start=_at(at),
            end=_at(at) + timedelta(minutes=30),
            source="ONLINE",
            full_name="Ana Martin",
            birth_date=date(1990, 5, 17),
            email="ana@example.org",
            expires_at=expires_at,
        )
        return Id(record.id)

    booking.labels[f"hold {hhmm}"] = booking.labels["hold"] = hold(
        hhmm, NOW + timedelta(minutes=10)
    )
    hold("11:30", NOW - timedelta(minutes=1))
