"""Steps of the admin's FHIR reference writes, compared with the console doing the same."""

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from string import Template
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.identity.domain.user import Role, User
from drlibre.interfaces.fhir.mappers import directory_writes as writes
from drlibre.interfaces.fhir.mappers.directory import (
    ORGANIZATION_TYPE,
    PHYSICAL_TYPE,
    PRODUCT_CODE,
    code_system_url,
    extension_url,
)
from drlibre.interfaces.fhir.schemas.directory import (
    CodeSystem,
    HealthcareService,
    Location,
    Organization,
    PractitionerRole,
    ValueSet,
)
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoClinicianProfiles,
    DjangoRooms,
)
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import PASSWORD, stored_session, stored_user, unique_email
from tests.fhir.conftest import token_for
from tests.fhir.directory_scene import Directory, django_repos
from tests.fhir.directory_steps import Exchange

_FHIR_JSON = "application/fhir+json"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass
class Writing:
    """Users' tokens, the resource last written and the audit entries left meanwhile."""

    exchange: Exchange
    tokens: dict[str, str] = field(default_factory=dict)
    users: dict[str, User] = field(default_factory=dict)
    written: str | None = None
    audit_count: int = 0
    trails: list[list[tuple[object, ...]]] = field(default_factory=list)
    extra_user: User | None = None
    sent: dict[str, Any] = field(default_factory=dict)

    @property
    def directory(self) -> Directory:
        assert self.exchange.directory is not None
        return self.exchange.directory

    def user(self, who: str) -> User:
        if who not in self.users:
            self.users[who] = (
                stored_user(Role.PATIENT) if who == "patient" else getattr(self.directory, who)
            )
        return self.users[who]

    def headers(self, who: str, **extra: str) -> dict[str, str]:
        if who not in self.tokens:
            self.tokens[who] = token_for(self.user(who))
        return {"Authorization": f"Bearer {self.tokens[who]}", **extra}

    def path(self, raw: str) -> str:
        return Template(raw).substitute(self.directory.ids(), patient=str(self.user("patient").id))

    def send(self, who: str, method: str, path: str, body: Any = None, **headers: str) -> Any:
        data = json.dumps(body) if body is not None else ""
        self.exchange.response = Client().generic(
            method, path, data, content_type=_FHIR_JSON, headers=self.headers(who, **headers)
        )
        return self.exchange.response

    def read(self, path: str) -> Any:
        return Client().get(path, headers=self.headers("admin"))


@pytest.fixture
def writing(exchange: Exchange) -> Writing:
    return Writing(exchange)


def _code(value: str) -> list[dict[str, str]]:
    return [{"system": PRODUCT_CODE, "value": value}]


def _ext(name: str, **value: Any) -> dict[str, Any]:
    return {"url": extension_url(name), **value}


def _sample(w: Writing, name: str) -> dict[str, Any]:
    """A resource as an external tool would send it, without id or meta."""
    d = w.directory
    if name == "hôpital":
        return {
            "resourceType": "Organization",
            "extension": [
                _ext("time-zone", valueCode="Europe/Paris"),
                _ext(
                    "position",
                    extension=[
                        {"url": "latitude", "valueDecimal": 50.69},
                        {"url": "longitude", "valueDecimal": 3.17},
                    ],
                ),
                _ext("description", valueString="Urgences 24 h sur 24."),
            ],
            "identifier": _code("HEST"),
            "active": True,
            "type": [{"coding": [{"system": ORGANIZATION_TYPE, "code": "prov"}]}],
            "name": "Hôpital Est",
            "telecom": [{"system": "phone", "value": "+33 3 20 11 22 33"}],
            "address": [
                {
                    "line": ["2 rue du Parc"],
                    "city": "Tourcoing",
                    "postalCode": "59200",
                    "country": "France",
                }
            ],
        }
    if name == "département":
        return {
            "resourceType": "Organization",
            "extension": [_ext("description", valueString="Explorations du sommeil.")],
            "identifier": _code("NEURO"),
            "active": True,
            "type": [{"coding": [{"system": ORGANIZATION_TYPE, "code": "dept"}]}],
            "name": "Neurologie",
            "partOf": {"reference": f"Organization/{d.lille.id}"},
        }
    if name == "salle":
        return {
            "resourceType": "Location",
            "extension": [
                _ext("floor", valueString="2"),
                _ext("capacity", valueInteger=4),
                _ext("equipment", valueString="ECG"),
                _ext("equipment", valueString="Tapis"),
            ],
            "identifier": _code("S9"),
            "status": "active",
            "name": "Salle 9",
            "physicalType": {"coding": [{"system": PHYSICAL_TYPE, "code": "ro"}]},
            "managingOrganization": {"reference": f"Organization/{d.cardiology.id}"},
        }
    if name == "type de RDV":
        return {
            "resourceType": "HealthcareService",
            "extension": [
                _ext("duration-minutes", valueInteger=45),
                _ext("buffer-minutes", valueInteger=10),
                _ext("colour", valueString="#AA3366"),
                _ext("needs-room", valueBoolean=True),
                _ext("bookable-online", valueBoolean=False),
            ],
            "identifier": _code("BILAN"),
            "active": True,
            "providedBy": {"reference": f"Organization/{d.cardiology.id}"},
            "name": "Bilan",
        }
    if name == "spécialité":
        return {
            "resourceType": "CodeSystem",
            "name": "NEURO",
            "title": "Neurologie",
            "status": "active",
            "concept": [{"code": "NEURO", "display": "Neurologie"}],
        }
    if name == "jeu de valeurs de spécialité":
        return {
            "resourceType": "ValueSet",
            "name": "NEURO",
            "title": "Neurologie",
            "status": "active",
            "compose": {"include": [{"concept": [{"code": "NEURO"}]}]},
        }
    if name in ("praticien", "patient"):
        return {
            "resourceType": "Practitioner" if name == "praticien" else "Patient",
            "extension": [_ext(writes.TEMPORARY_PASSWORD, valueString=PASSWORD)],
            "active": True,
            "name": [{"text": "Chloé Durand"}],
            "telecom": [{"system": "email", "value": unique_email("chloe")}],
        }
    if name == "profil praticien":
        if w.extra_user is None:
            w.extra_user = stored_user(Role.CLINICIAN)
        return {
            "resourceType": "PractitionerRole",
            "extension": [
                _ext("title", valueString="Dr"),
                _ext("bio", valueString="Rythmologue"),
                _ext("round-robin-weight", valueInteger=5),
            ],
            "active": True,
            "practitioner": {"reference": f"Practitioner/{w.extra_user.id}"},
            "organization": {"reference": f"Organization/{d.cardiology.id}"},
            "specialty": [{"coding": [{"system": code_system_url(d.specialty.id)}]}],
            "location": [{"reference": f"Location/{d.room.id}"}],
        }
    raise AssertionError(name)


def _label(resource: dict[str, Any]) -> str:
    kind = resource["resourceType"]
    if kind in ("Practitioner", "Patient"):
        return resource["name"][0]["text"]
    if kind in ("CodeSystem", "ValueSet"):
        return resource["title"]
    if kind == "PractitionerRole":
        return next(e["valueString"] for e in resource["extension"] if e["url"].endswith("/bio"))
    return resource["name"]


def _renamed(resource: dict[str, Any]) -> dict[str, Any]:
    found = copy.deepcopy(resource)
    kind = found["resourceType"]
    if kind in ("Practitioner", "Patient"):
        found["name"][0]["text"] += " bis"
    elif kind in ("CodeSystem", "ValueSet"):
        found["title"] += " bis"
    elif kind == "PractitionerRole":
        for e in found["extension"]:
            if e["url"].endswith("/bio"):
                e["valueString"] += " bis"
    else:
        found["name"] += " bis"
    return found


def _put(
    w: Writing, who: str, change: Callable[[dict[str, Any]], None], stale: bool = False
) -> None:
    assert w.written is not None
    current = w.read(w.written)
    resource = current.json()
    change(resource)
    etag = 'W/"stale"' if stale else current["ETag"]
    w.send(who, "PUT", w.written, resource, **{"If-Match": etag})


@when(parsers.parse('"{who}" creates the "{sample}" in FHIR'))
def creates(writing: Writing, who: str, sample: str) -> None:
    resource = writing.sent = _sample(writing, sample)
    response = writing.send(who, "POST", f"/fhir/{resource['resourceType']}", resource)
    assert response.status_code == 201, response.content
    writing.written = f"/fhir/{resource['resourceType']}/{response.json()['id']}"


@when(parsers.parse('"{who}" creates the "{sample}" with the code of "{record}"'))
def creates_with_code(writing: Writing, who: str, sample: str, record: str) -> None:
    resource = _sample(writing, sample)
    resource["identifier"] = _code(getattr(writing.directory, record).code)
    writing.send(who, "POST", f"/fhir/{resource['resourceType']}", resource)


@then(parsers.parse('the client is answered 201 with the "{resource}" written'))
def answered_created(writing: Writing, resource: str) -> None:
    response = writing.exchange.response
    body = response.json()
    assert writing.written == f"/fhir/{resource}/{body['id']}"
    assert response["Location"].endswith(writing.written)
    assert response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    assert writing.read(writing.written).json() == body
    _keeps_what_was_sent(writing.sent, body)


# Written only, or rendered in another element: the title is the practitioner's name prefix.
_NOT_READ_BACK = {extension_url(writes.TEMPORARY_PASSWORD), extension_url("title")}


def _keeps_what_was_sent(sent: dict[str, Any], body: dict[str, Any]) -> None:
    """Every element sent is read back, so an update from the read loses nothing."""
    for key, value in sent.items():
        if key == "extension":
            kept = [e for e in value if e["url"] not in _NOT_READ_BACK]
            assert all(e in body["extension"] for e in kept), (kept, body.get("extension"))
        elif key == "location":
            assert all(v in body[key] for v in value), body[key]
        elif key == "compose":
            concepts = [c for i in body[key]["include"] for c in i["concept"]]
            assert [c for i in value["include"] for c in i["concept"]] == concepts
        elif key == "specialty":
            systems = [c["system"] for k in body[key] for c in k["coding"]]
            assert [c["system"] for k in value for c in k["coding"]] == systems
        else:
            assert body[key] == value, (key, body.get(key))


@then("the answer carries no temporary password")
def no_password(writing: Writing) -> None:
    assert PASSWORD not in writing.exchange.response.content.decode()
    assert writes.TEMPORARY_PASSWORD not in writing.exchange.response.content.decode()


@when(parsers.parse('"{who}" renames the written "{resource}" under its version'))
def renames(writing: Writing, who: str, resource: str) -> None:
    _put(writing, who, lambda r: r.update(_renamed(r)))


@when(parsers.parse('"{who}" renames the written "{resource}" under a stale version'))
def renames_stale(writing: Writing, who: str, resource: str) -> None:
    _put(writing, who, lambda r: r.update(_renamed(r)), stale=True)


@then(parsers.parse('the client is answered 200 with the "{resource}" renamed'))
def answered_renamed(writing: Writing, resource: str) -> None:
    response = writing.exchange.response
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["resourceType"] == resource
    assert _label(body).endswith(" bis")
    assert response["ETag"] == f'W/"{body["meta"]["versionId"]}"'


@then(parsers.parse('the written "{resource}" keeps its name'))
def keeps_name(writing: Writing, resource: str) -> None:
    assert writing.written is not None
    assert not _label(writing.read(writing.written).json()).endswith(" bis")


@when(parsers.parse('"{who}" deletes the written "{resource}"'))
def deletes(writing: Writing, who: str, resource: str) -> None:
    assert writing.written is not None
    writing.send(who, "DELETE", writing.written)


@then(parsers.parse('the client is answered 204 and the written "{resource}" is gone'))
def gone(writing: Writing, resource: str) -> None:
    assert writing.exchange.response.status_code == 204, writing.exchange.response.content
    assert writing.written is not None
    assert writing.read(writing.written).status_code == 404


@when(parsers.parse('"{who}" sends "{method}" to "{path}" with the "{sample}"'))
def sends(writing: Writing, who: str, method: str, path: str, sample: str) -> None:
    body = _sample(writing, sample)
    writing.headers(who)
    writing.audit_count = AuditEntryRecord.objects.count()
    writing.send(who, method, writing.path(path), body)


@then("no audit entry was left")
def nothing_written(writing: Writing) -> None:
    assert AuditEntryRecord.objects.count() == writing.audit_count


@then(
    parsers.parse(
        'the written specialty reads as a "{first}" and a "{second}" of the same id and title'
    )
)
def same_specialty(writing: Writing, first: str, second: str) -> None:
    record = _written_id(writing)
    bodies = [writing.read(f"/fhir/{kind}/{record}").json() for kind in (first, second)]
    assert {(b["id"], b["title"]) for b in bodies} == {(str(record), "Neurologie")}
    include = bodies[1]["compose"]["include"]
    assert [i["system"] for i in include] == [code_system_url(record)]


@then(parsers.parse('the written specialty is gone as a "{kind}" too'))
def gone_too(writing: Writing, kind: str) -> None:
    assert writing.exchange.response.status_code == 204, writing.exchange.response.content
    assert writing.read(f"/fhir/{kind}/{_written_id(writing)}").status_code == 404


@when(parsers.parse('"{who}" changes the birth date of the written "{resource}" under its version'))
def changes_birth_date(writing: Writing, who: str, resource: str) -> None:
    _put(writing, who, lambda r: r.update(birthDate="1990-01-01"))


@then(
    parsers.parse(
        'the stored room has the floor "{floor}", the capacity {capacity:d} and the equipment'
        ' "{equipment}"'
    )
)
def stored_room(writing: Writing, floor: str, capacity: int, equipment: str) -> None:
    room = DjangoRooms().get(_written_id(writing))
    assert room is not None
    assert (room.floor, room.capacity, room.equipment) == (
        floor,
        capacity,
        tuple(equipment.split(", ")),
    )


@then(
    parsers.parse(
        "the stored type lasts {duration:d} minutes plus {buffer:d}, is coloured"
        ' "{colour}", needs a room and is booked offline'
    )
)
def stored_type(writing: Writing, duration: int, buffer: int, colour: str) -> None:
    kind = DjangoAppointmentTypes().get(_written_id(writing))
    assert kind is not None
    assert (kind.duration_minutes, kind.buffer_minutes, kind.colour) == (duration, buffer, colour)
    assert (kind.needs_room, kind.bookable_online) == (True, False)


@then(parsers.parse("the stored profile weighs {weight:d} in round robin"))
def stored_profile(writing: Writing, weight: int) -> None:
    profile = DjangoClinicianProfiles().get(_written_id(writing))
    assert profile is not None
    assert profile.weight == weight


@then(parsers.parse('the written "PractitionerRole" shows the round robin weight {weight:d}'))
def role_weight(writing: Writing, weight: int) -> None:
    assert writing.written is not None
    body = writing.read(writing.written).json()
    assert _ext("round-robin-weight", valueInteger=weight) in body["extension"]


def _written_id(writing: Writing) -> Id:
    assert writing.written is not None
    return Id.parse(writing.written.rpartition("/")[2])


def _details(writing: Writing) -> dict[str, Any]:
    return json.loads(writing.exchange.response.json()["issue"][0]["diagnostics"])


@then(parsers.parse('the outcome names the field "{name}" with the console\'s message "{message}"'))
def names_field(writing: Writing, name: str, message: str) -> None:
    assert _details(writing)["fields"] == [{"field": name, "message": message}]


@then(
    parsers.re(
        r'the outcome lists (?:the room "(?P<rooms>[^"]*)", )?'
        r'(?:the types "(?P<types>[^"]*)" and )?the profiles "(?P<profiles>[^"]*)"'
    )
)
def lists_dependents(
    writing: Writing, profiles: str, rooms: str | None = None, types: str | None = None
) -> None:
    named = [n.strip() for raw in (rooms, types, profiles) if raw for n in raw.split(",")]
    wanted = {writing.path(f"${n}") for n in named}
    assert {d["id"] for d in _details(writing)["dependents"]} == wanted


@when(parsers.parse('"{who}" moves the room "{room}" to another department under its version'))
def moves_room(writing: Writing, who: str, room: str) -> None:
    other = build.department(writing.directory.lille.id, name="Pneumologie")
    django_repos().departments.save(other)
    writing.written = writing.path(f"/fhir/Location/${room}")
    _put(
        writing,
        who,
        lambda r: r.update(managingOrganization={"reference": f"Organization/{other.id}"}),
    )


_OWN_CHANGES: dict[str, Callable[[dict[str, Any]], None]] = {
    "inactive": lambda r: r.update(active=False),
    "role clinician": lambda r: r.update(extension=[_ext(writes.ROLE, valueCode="clinician")]),
}


@when(parsers.parse('"{who}" sends their own practitioner with "{change}" under its version'))
def own_practitioner(writing: Writing, who: str, change: str) -> None:
    writing.written = f"/fhir/Practitioner/{writing.user(who).id}"
    _put(writing, who, _OWN_CHANGES[change])


# The console's screens for each sample: create and delete URLs, edit URL by id.
_CONSOLE = {
    "hôpital": ("hospitals", "hospital"),
    "département": ("departments", "department"),
    "salle": ("rooms", "room"),
    "type de RDV": ("appointment-types", "appointment_type"),
    "spécialité": ("specialties", "specialty"),
    "jeu de valeurs de spécialité": ("specialties", "specialty"),
    "praticien": ("users", "user"),
    "patient": ("users", "user"),
    "profil praticien": ("clinicians", "clinician_profile"),
}


def _console_form(writing: Writing, sample: str) -> dict[str, str]:
    """The console form an admin fills for the same record as the FHIR sample."""
    resource = _sample(writing, sample)
    if sample == "hôpital":
        return writes.hospital_fields(Organization.model_validate(resource))
    if sample == "département":
        return writes.department_fields(Organization.model_validate(resource))
    if sample == "salle":
        return writes.room_fields(Location.model_validate(resource))
    if sample == "type de RDV":
        return writes.type_fields(HealthcareService.model_validate(resource))
    if sample == "spécialité":
        return writes.specialty_fields(CodeSystem.model_validate(resource))
    if sample == "jeu de valeurs de spécialité":
        return writes.value_set_fields(ValueSet.model_validate(resource))
    if sample == "profil praticien":
        assert writing.extra_user is not None
        role = PractitionerRole.model_validate(resource)
        fields = writes.profile_fields(role, room_id=str(writing.directory.room.id), title="")
        return fields | {"user_id": str(writing.extra_user.id)}
    return {
        "full_name": resource["name"][0]["text"],
        "email": resource["telecom"][0]["value"],
        "role": "clinician" if sample == "praticien" else "patient",
        "active": "on",
        "temporary_password": PASSWORD,
    }


def _console_renamed(sample: str, form: dict[str, str]) -> dict[str, str]:
    key = {"praticien": "full_name", "patient": "full_name", "profil praticien": "bio"}
    name = key.get(sample, "name")
    return form | {name: f"{form[name]} bis"}


def _trail(entity_id: object) -> list[tuple[object, ...]]:
    """The entity's audit entries, ids blanked so two records' trails compare."""
    rows = AuditEntryRecord.objects.filter(entity_id=entity_id).order_by("at", "action")
    return [
        (
            r.action,
            r.entity_type,
            r.actor_id,
            json.loads(_UUID.sub("<id>", json.dumps(r.metadata, sort_keys=True))),
        )
        for r in rows
    ]


@when(parsers.parse('"{who}" creates, renames and deletes the "{sample}" in FHIR'))
def fhir_lifecycle(writing: Writing, who: str, sample: str) -> None:
    creates(writing, who, sample)
    renames(writing, who, "")
    assert writing.exchange.response.status_code == 200, writing.exchange.response.content
    deletes(writing, who, "")
    assert writing.exchange.response.status_code == 204, writing.exchange.response.content
    writing.trails.append(_trail(_written_id(writing).value))


@when(parsers.parse('"{who}" creates, renames and deletes the "{sample}" on the console'))
def console_lifecycle(writing: Writing, who: str, sample: str) -> None:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(writing.user(who))
    slug, entity = _CONSOLE[sample]
    form = _console_form(writing, sample)
    seen = set(AuditEntryRecord.objects.values_list("id", flat=True))
    assert client.post(f"/console/{slug}/new", form).status_code == 302
    created = AuditEntryRecord.objects.exclude(id__in=seen).get(action=f"{entity}.created")
    base = f"/console/{slug}/{created.entity_id}"
    assert client.post(f"{base}/edit", _console_renamed(sample, form)).status_code == 302
    assert client.post(f"{base}/delete").status_code == 302
    writing.trails.append(_trail(created.entity_id))


@then(parsers.parse('both leave the same audit entries "{actions}"'))
def same_audit(writing: Writing, actions: str) -> None:
    fhir, console = writing.trails
    assert [entry[0] for entry in fhir] == actions.split(", ")
    assert fhir == console
    assert {entry[2] for entry in fhir} == {writing.directory.admin.id.value}
