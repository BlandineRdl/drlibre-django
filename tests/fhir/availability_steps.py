"""Steps of the clinician's FHIR availability, compared with the workspace screens."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from string import Template
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.bootstrap.container import container, real_adapters, use_container, wire
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interfaces.fhir.mappers.directory import extension_url
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.room import Room
from drlibre.organisation.infrastructure.repositories import (
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoRooms,
)
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_session
from tests.builders_scheduling import rule as a_rule
from tests.fakes.clock import FixedClock
from tests.fhir.conftest import token_for
from tests.fhir.directory_scene import Directory
from tests.fhir.directory_steps import Exchange
from tests.fhir.reference_write_steps import _trail
from tests.fhir.slot_steps import PARIS, slots_are

_FHIR_JSON = "application/fhir+json"
_AVAILABILITY = ("availability_rule", "time_off")


@dataclass
class Agenda:
    """The clinician's colleague elsewhere, the schedule last written and the audit meanwhile."""

    exchange: Exchange
    colleague: User | None = None
    colleague_profile: ClinicianProfile | None = None
    colleague_rule: Id | None = None
    other_room: Room | None = None
    appointment: uuid.UUID | None = None
    written: str | None = None
    audit_count: int = 0
    trails: list[list[tuple[object, ...]]] = field(default_factory=list)
    tokens: dict[str, str] = field(default_factory=dict)

    @property
    def directory(self) -> Directory:
        assert self.exchange.directory is not None
        return self.exchange.directory

    def user(self, who: str) -> User:
        found = self.colleague if who == "colleague" else getattr(self.directory, who)
        assert found is not None
        return found

    def path(self, raw: str) -> str:
        assert self.colleague_profile is not None
        assert self.other_room is not None
        assert self.colleague is not None
        return Template(raw).substitute(
            self.directory.ids(),
            colleague=str(self.colleague.id),
            colleague_profile=str(self.colleague_profile.id),
            colleague_rule=str(self.colleague_rule),
            other_room=str(self.other_room.id),
        )

    def headers(self, who: str, **extra: str) -> dict[str, str]:
        if who not in self.tokens:
            self.tokens[who] = token_for(self.user(who))
        return {"Authorization": f"Bearer {self.tokens[who]}", **extra}

    def send(self, who: str, method: str, path: str, body: Any = None, **headers: str) -> Any:
        self.audit_count = _audit_count()
        data = json.dumps(body) if body is not None else ""
        self.exchange.response = Client().generic(
            method, path, data, content_type=_FHIR_JSON, headers=self.headers(who, **headers)
        )
        return self.exchange.response

    def read(self, who: str, path: str) -> Any:
        return Client().get(path, headers=self.headers(who))

    def body(self) -> Any:
        return self.exchange.response.json()


@pytest.fixture
def agenda(exchange: Exchange) -> Agenda:
    return Agenda(exchange)


def _audit_count() -> int:
    return AuditEntryRecord.objects.filter(entity_type__in=_AVAILABILITY).count()


def _colleague() -> User:
    return User(
        id=Id(),
        email=Email(f"chloe.{Id().value.hex[:6]}@example.org"),
        full_name="Chloé Durand",
        role=Role.CLINICIAN,
        active=True,
        password_hash=None,
        must_change_password=False,
        last_login_at=None,
        created_at=build.AT,
        updated_at=build.AT,
    )


@given(
    parsers.parse(
        'on "{today}" the clinician is booked at "{booked}" on "{day}" and a colleague works in'
        " another department"
    )
)
def agenda_scene(agenda: Agenda, fixed_clock: None, today: str, booked: str, day: str) -> None:
    scene = agenda.directory
    use_container(wire(real_adapters(FixedClock(datetime.fromisoformat(f"{today}T10:00+00:00")))))
    neurology = build.department(scene.paris.id, name="Neurologie")
    DjangoDepartments().save(neurology)
    agenda.other_room = build.room(neurology.id, name="Salle 2")
    DjangoRooms().save(agenda.other_room)
    agenda.colleague = _colleague()
    DjangoUsers().save(agenda.colleague)
    raw = {
        "department_id": str(neurology.id),
        "specialty_id": str(scene.specialty.id),
        "title": "Dr",
    }
    agenda.colleague_profile = ClinicianProfile.attach(
        raw, user_id=agenda.colleague.id, at=build.AT
    )
    DjangoClinicianProfiles().save(agenda.colleague_profile)
    rule = a_rule(agenda.colleague_profile.id, weekday=3, room_id=agenda.other_room.id)
    DjangoAvailabilityRules().save(rule)
    agenda.colleague_rule = rule.id
    start = datetime.combine(date.fromisoformat(day), time.fromisoformat(booked), tzinfo=PARIS)
    agenda.appointment = AppointmentRecord.objects.create(
        patient_id=uuid.uuid4(),
        clinician_id=scene.profile.id.value,
        appointment_type_id=scene.online.id.value,
        start=start,
        end=start + timedelta(minutes=30),
        status="BOOKED",
        source="ONLINE",
    ).id
    container().extend_slot_horizon.execute()


# Schedule
_DAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")


def _schedule(
    agenda: Agenda, who: str, day: str, start: str, end: str, step: int, room: str
) -> dict[str, Any]:
    hours = [
        {"url": "weekday", "valueCode": day},
        {"url": "start", "valueTime": f"{start}:00"},
        {"url": "end", "valueTime": f"{end}:00"},
        {"url": "step-minutes", "valueInteger": step},
    ]
    return {
        "resourceType": "Schedule",
        "extension": [{"url": extension_url("availability"), "extension": hours}],
        "actor": [
            {"reference": f"Practitioner/{agenda.user(who).id}"},
            {"reference": f"Location/{agenda.path(room)}"},
        ],
    }


@when(
    parsers.parse(
        '"{who}" creates a schedule on "{day}" from "{start}" to "{end}" every {step:d} minutes'
        ' in "{room}"'
    )
)
def creates_schedule(
    agenda: Agenda, who: str, day: str, start: str, end: str, step: int, room: str
) -> None:
    body = _schedule(agenda, who, day, start, end, step, room)
    response = agenda.send(who, "POST", "/fhir/Schedule", body)
    if response.status_code == 201:
        agenda.written = f"/fhir/Schedule/{response.json()['id']}"


@when(parsers.parse('"{who}" creates a schedule with the horizon "{start}"'))
def creates_with_horizon(agenda: Agenda, who: str, start: str) -> None:
    body = _schedule(agenda, who, "tue", "14:00", "15:00", 30, "$room")
    agenda.send(who, "POST", "/fhir/Schedule", body | {"planningHorizon": {"start": start}})


def _put(agenda: Agenda, who: str, path: str, change: Any, stale: bool = False) -> None:
    current = agenda.read(who, path)
    assert current.status_code == 200, current.content
    resource = current.json()
    change(resource)
    etag = 'W/"stale"' if stale else current["ETag"]
    agenda.send(who, "PUT", path, resource, **{"If-Match": etag})


@when(parsers.parse('"{who}" updates the schedule ${record} with the horizon "{start}"'))
def updates_horizon(agenda: Agenda, who: str, record: str, start: str) -> None:
    def change(resource: dict[str, Any]) -> None:
        resource["planningHorizon"]["start"] = start

    _put(agenda, who, agenda.path(f"/fhir/Schedule/${record}"), change)


@when(parsers.parse('"{who}" moves the end of the written schedule to "{end}" under its version'))
def moves_end(agenda: Agenda, who: str, end: str) -> None:
    def change(resource: dict[str, Any]) -> None:
        for e in resource["extension"][0]["extension"]:
            if e["url"] == "end":
                e["valueTime"] = f"{end}:00"

    assert agenda.written is not None
    _put(agenda, who, agenda.written, change)


@when(parsers.parse('"{who}" deletes the written schedule'))
def deletes_schedule(agenda: Agenda, who: str) -> None:
    assert agenda.written is not None
    agenda.send(who, "DELETE", agenda.written)


@then(
    parsers.parse(
        'the client is answered {status:d} with the schedule of "{who}" in "{room}" on "{day}"'
        ' from "{start}" to "{end}" every {step:d} minutes'
    )
)
def answered_schedule(
    agenda: Agenda, status: int, who: str, room: str, day: str, start: str, end: str, step: int
) -> None:
    body = agenda.body()
    assert agenda.exchange.response.status_code == status, body
    assert agenda.exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    if status == 201:
        assert agenda.exchange.response["Location"].endswith(f"/Schedule/{body['id']}")
    assert [a["reference"] for a in body["actor"]] == [
        f"Practitioner/{agenda.user(who).id}",
        f"Location/{agenda.path(room)}",
    ]
    (hours,) = body["extension"]
    assert hours["url"] == extension_url("availability")
    assert hours["extension"] == [
        {"url": "weekday", "valueCode": day},
        {"url": "start", "valueTime": start},
        {"url": "end", "valueTime": end},
        {"url": "step-minutes", "valueInteger": step},
    ]


@then(parsers.parse('the written schedule runs from "{start}" with no end'))
def runs_from(agenda: Agenda, start: str) -> None:
    assert agenda.body()["planningHorizon"] == {"start": start}


@then(parsers.parse('the role "{role}" shows the hours "{hours}"'))
def role_hours(agenda: Agenda, role: str, hours: str) -> None:
    body = agenda.read("clinician", agenda.path(f"/fhir/PractitionerRole/{role}")).json()
    found = [
        f"{a['daysOfWeek'][0]} {a['availableStartTime']}-{a['availableEndTime']}"
        for a in body["availableTime"]
    ]
    assert sorted(found, key=lambda h: _DAYS.index(h[:3])) == hours.split(", ")


@then("the client is answered 204 and the written schedule is gone")
def schedule_gone(agenda: Agenda) -> None:
    assert agenda.exchange.response.status_code == 204
    assert agenda.written is not None
    assert agenda.read("clinician", agenda.written).status_code == 404


@when(parsers.parse('"{who}" sends "{method}" to "{path}" with a schedule of "{named}"'))
def sends_schedule(agenda: Agenda, who: str, method: str, path: str, named: str) -> None:
    room = "$other_room" if named == "colleague" else "$room"
    body = _schedule(agenda, named, "wed", "08:00", "09:00", 30, room)
    agenda.send(who, method, agenda.path(path), None if method == "DELETE" else body)


@then(parsers.re(r'the FHIR slots of "(?P<day>[^"]+)" are "(?P<slots>[^"]*)"'))
def slots_of(agenda: Agenda, day: str, slots: str) -> None:
    first = date.fromisoformat(day)
    window = (
        f"start=ge{first}T00:00:00%2B01:00&start=lt{first + timedelta(days=1)}T00:00:00%2B01:00"
    )
    path = agenda.path(f"/fhir/Slot?service-type=$online&{window}")
    agenda.exchange.response = Client().get(path)
    slots_are(agenda.exchange, slots)


@then("no availability audit entry was left")
def no_audit(agenda: Agenda) -> None:
    assert _audit_count() == agenda.audit_count


@then(parsers.parse('the outcome names only the field "{name}"'))
def names_field(agenda: Agenda, name: str) -> None:
    details = json.loads(agenda.body()["issue"][0]["diagnostics"])
    assert [f["field"] for f in details["fields"]] == [name]


# PractitionerRole.notAvailable
def _period(reason: str, start: str, end: str) -> dict[str, Any]:
    return {"description": reason, "during": {"start": start, "end": end}}


def _own_role(agenda: Agenda) -> str:
    return f"/fhir/PractitionerRole/{agenda.directory.profile.id}"


@when(
    parsers.parse(
        '"{who}" adds to their role the time off "{reason}" from "{start}" to "{end}" under its'
        " version"
    )
)
def adds_time_off(agenda: Agenda, who: str, reason: str, start: str, end: str) -> None:
    def change(resource: dict[str, Any]) -> None:
        resource["notAvailable"].append(_period(reason, start, end))

    _put(agenda, who, _own_role(agenda), change)


@when(
    parsers.parse(
        '"{who}" adds to their role the time off "{reason}" from "{start}" to "{end}" under a'
        " stale version"
    )
)
def adds_time_off_stale(agenda: Agenda, who: str, reason: str, start: str, end: str) -> None:
    def change(resource: dict[str, Any]) -> None:
        resource["notAvailable"].append(_period(reason, start, end))

    _put(agenda, who, _own_role(agenda), change, stale=True)


@when(
    parsers.parse(
        '"{who}" adds to their role the time offs "{first}" from "{first_start}" to "{first_end}"'
        ' then "{second}" from "{second_start}" to "{second_end}"'
    )
)
def adds_two_time_offs(
    agenda: Agenda,
    who: str,
    first: str,
    first_start: str,
    first_end: str,
    second: str,
    second_start: str,
    second_end: str,
) -> None:
    resource = agenda.read(who, _own_role(agenda)).json()
    resource["notAvailable"] += [
        _period(first, first_start, first_end),
        _period(second, second_start, second_end),
    ]
    agenda.send(who, "PUT", _own_role(agenda), resource)


@when(
    parsers.parse(
        '"{who}" adds to the role "{role}" the time off "{reason}" from "{start}" to "{end}"'
    )
)
def adds_to_other_role(
    agenda: Agenda, who: str, role: str, reason: str, start: str, end: str
) -> None:
    path = agenda.path(f"/fhir/PractitionerRole/{role}")
    resource = agenda.read(who, path).json()
    resource["notAvailable"] = [*resource.get("notAvailable", []), _period(reason, start, end)]
    agenda.send(who, "PUT", path, resource)


@when(parsers.parse('"{who}" removes from their role the time off "{reason}" under its version'))
def removes_time_off(agenda: Agenda, who: str, reason: str) -> None:
    def change(resource: dict[str, Any]) -> None:
        resource["notAvailable"] = [
            n for n in resource["notAvailable"] if n["description"] != reason
        ]

    _put(agenda, who, _own_role(agenda), change)


@when(parsers.parse('"{who}" changes the hours of their role to "{hours}" under its version'))
def changes_hours(agenda: Agenda, who: str, hours: str) -> None:
    day, _, span = hours.partition(" ")
    start, _, end = span.partition("-")

    def change(resource: dict[str, Any]) -> None:
        resource["availableTime"] = [
            {"daysOfWeek": [day], "availableStartTime": start, "availableEndTime": end}
        ]

    _put(agenda, who, _own_role(agenda), change)


_OTHER_CHANGES: dict[str, Any] = {
    "bio": lambda r: r.update(extension=[{"url": extension_url("bio"), "valueString": "Autre"}]),
    "active": lambda r: r.update(active=False),
    "location": lambda r: r.update(location=r["location"][:1]),
}


@when(parsers.parse('"{who}" changes "{element}" of their role under its version'))
def changes_other(agenda: Agenda, who: str, element: str) -> None:
    _put(agenda, who, _own_role(agenda), _OTHER_CHANGES[element])


@then(parsers.parse('the client is answered 200 with the time offs "{reasons}"'))
def answered_time_offs(agenda: Agenda, reasons: str) -> None:
    body = agenda.body()
    assert agenda.exchange.response.status_code == 200, body
    assert agenda.exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    assert sorted(n["description"] for n in body["notAvailable"]) == reasons.split(", ")


@then(parsers.parse('the clinician\'s stored time offs are "{reasons}"'))
def stored_time_offs(agenda: Agenda, reasons: str) -> None:
    found = DjangoTimeOffs().for_clinician(agenda.directory.profile.id)
    assert sorted(t.reason for t in found) == reasons.split(", ")


@then(parsers.parse('the clinician\'s appointment at "{at}" on "{day}" is still booked'))
def still_booked(agenda: Agenda, at: str, day: str) -> None:
    found = AppointmentRecord.objects.get(id=agenda.appointment)
    start = datetime.combine(date.fromisoformat(day), time.fromisoformat(at), tzinfo=PARIS)
    assert (found.status, found.start) == ("BOOKED", start.astimezone(UTC))


# Same audit as the workspace screens
def _seen() -> set[uuid.UUID]:
    return set(AuditEntryRecord.objects.values_list("id", flat=True))


def _new(seen: set[uuid.UUID], action: str) -> uuid.UUID:
    """The entity of the one `action` entry written since `seen`; the clock is fixed."""
    found = AuditEntryRecord.objects.exclude(id__in=seen).get(action=action).entity_id
    assert found is not None
    return found


def _workspace(agenda: Agenda, who: str) -> Client:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(agenda.user(who))
    return client


@when(parsers.parse('"{who}" creates, changes and deletes a schedule in FHIR'))
def fhir_schedule_lifecycle(agenda: Agenda, who: str) -> None:
    seen = _seen()
    creates_schedule(agenda, who, "tue", "14:00", "15:00", 30, "$room")
    assert agenda.exchange.response.status_code == 201, agenda.body()
    moves_end(agenda, who, "16:00")
    assert agenda.exchange.response.status_code == 200, agenda.body()
    deletes_schedule(agenda, who)
    assert agenda.exchange.response.status_code == 204
    agenda.trails.append(_trail(_new(seen, "availability_rule.created")))


@when(parsers.parse('"{who}" creates, changes and deletes a schedule on the workspace'))
def workspace_schedule_lifecycle(agenda: Agenda, who: str) -> None:
    client = _workspace(agenda, who)
    seen = _seen()
    form = {
        "weekday": "2",
        "start": "14:00",
        "end": "15:00",
        "step_minutes": "30",
        "room_id": str(agenda.directory.room.id),
    }
    assert client.post("/workspace/availability/new", form).status_code == 302
    created = _new(seen, "availability_rule.created")
    base = f"/workspace/availability/{created}"
    assert client.post(f"{base}/edit", form | {"end": "16:00"}).status_code == 302
    assert client.post(f"{base}/delete").status_code == 302
    agenda.trails.append(_trail(created))


@when(parsers.parse('"{who}" adds and removes a time off in FHIR'))
def fhir_time_off_lifecycle(agenda: Agenda, who: str) -> None:
    seen = _seen()
    adds_time_off(
        agenda, who, "Formation", "2026-11-23T10:00:00+01:00", "2026-11-23T11:00:00+01:00"
    )
    assert agenda.exchange.response.status_code == 200, agenda.body()
    removes_time_off(agenda, who, "Formation")
    assert agenda.exchange.response.status_code == 200, agenda.body()
    agenda.trails.append(_trail(_new(seen, "time_off.created")))


@when(parsers.parse('"{who}" adds and removes a time off on the workspace'))
def workspace_time_off_lifecycle(agenda: Agenda, who: str) -> None:
    client = _workspace(agenda, who)
    seen = _seen()
    form = {"start": "2026-11-23T10:00", "end": "2026-11-23T11:00", "reason": "Formation"}
    assert client.post("/workspace/time-off/new", form).status_code == 302
    created = _new(seen, "time_off.created")
    assert client.post(f"/workspace/time-off/{created}/delete").status_code == 302
    agenda.trails.append(_trail(created))


@then(parsers.parse('both leave the same availability audit entries "{actions}" by "{who}"'))
def same_audit(agenda: Agenda, actions: str, who: str) -> None:
    fhir, workspace = agenda.trails
    # The clock is fixed, so entries come sorted by action, not in writing order.
    assert [entry[0] for entry in fhir] == sorted(actions.split(", "))
    assert fhir == workspace
    assert {entry[2] for entry in fhir} == {agenda.user(who).id.value}
