"""Steps of the FHIR `Patient` scenarios, on PostgreSQL, shared by their feature files."""

import dataclasses
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from string import Template
from typing import Any
from urllib.parse import quote

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interfaces.web.presenters.portal import PROFILE_URL
from tests.builders import stored_session, stored_user
from tests.builders_booking import existing_appointment, stored_scene
from tests.fhir.conftest import token_for
from tests.fhir.directory_steps import Exchange

_SEEN = datetime(2026, 1, 5, 9, tzinfo=UTC)


@dataclass
class Patients:
    """Two patients, a clinician who has seen the first one, an admin, and the last version read."""

    people: dict[str, User]
    version: str = ""
    previous: str = ""

    def ids(self) -> dict[str, str]:
        found = {name: str(user.id) for name, user in self.people.items()}
        return found | {"absent": "00000000-0000-4000-8000-000000000000"}


@pytest.fixture
def patients() -> Patients:
    return Patients({})


def _patient(name: str, phone: str, born: date) -> User:
    user = stored_user(Role.PATIENT)
    user = dataclasses.replace(user, full_name=name, phone=phone, birth_date=born)
    DjangoUsers().save(user)
    return user


def _headers(user: User | None, **extra: str) -> dict[str, str]:
    return ({"Authorization": f"Bearer {token_for(user)}"} if user else {}) | extra


@given("two patients, a clinician who has seen the first one and an admin")
def two_patients(patients: Patients) -> None:
    first = _patient("Anne Durand", "0611111111", date(1980, 3, 4))
    second = _patient("Bruno Petit", "0622222222", date(1990, 5, 1))
    scene = stored_scene()
    profile = scene.clinicians[0]
    seen = existing_appointment(
        patient_id=first.id,
        clinician_id=profile.id,
        appointment_type_id=scene.kind,
        start=_SEEN,
        end=_SEEN + timedelta(minutes=30),
    )
    DjangoAppointments().add(seen)
    clinician = DjangoUsers().get(profile.user_id)
    assert clinician is not None
    admin = stored_user(Role.ADMIN)
    patients.people = {
        "first": first,
        "second": second,
        "clinician": clinician,
        "admin": admin,
    }


def _who(patients: Patients, who: str) -> User | None:
    return None if who == "nobody" else patients.people[who]


@when(parsers.parse('"{who}" reads the patient "{target}"'))
def reads_patient(patients: Patients, exchange: Exchange, who: str, target: str) -> None:
    path = f"/fhir/Patient/{patients.ids()[target]}"
    exchange.response = Client().get(path, headers=_headers(_who(patients, who)))
    if exchange.response.status_code == 200:
        patients.version = exchange.body()["meta"]["versionId"]


@when(parsers.parse('"{who}" searches the patients with "{query}"'))
def searches_patients(patients: Patients, exchange: Exchange, who: str, query: str) -> None:
    values = {k: quote(v) for k, v in patients.ids().items()}
    values |= {f"{k}_email": quote(u.email.value) for k, u in patients.people.items()}
    path = f"/fhir/Patient?{Template(query).substitute(values)}"
    exchange.response = Client().get(path, headers=_headers(_who(patients, who)))


def _resource(patients: Patients, target: str, **changes: Any) -> dict[str, Any]:
    response = Client().get(
        f"/fhir/Patient/{patients.ids()[target]}", headers=_headers(patients.people["admin"])
    )
    body = response.json()
    patients.previous, patients.version = patients.version, body["meta"]["versionId"]
    for path, value in changes.items():
        if path == "phone":
            body["telecom"] = [c for c in body["telecom"] if c["system"] != "phone"]
            body["telecom"].append({"system": "phone", "value": value})
        elif path == "email":
            body["telecom"] = [
                c if c["system"] != "email" else {"system": "email", "value": value}
                for c in body["telecom"]
            ]
        elif path == "name":
            body["name"] = [{"text": value}]
        else:
            body[path] = value
    return body


def _put(exchange: Exchange, who: User | None, target_id: str, body: Any, version: str) -> None:
    headers = _headers(who, **({"If-Match": f'W/"{version}"'} if version else {}))
    exchange.response = Client().put(
        f"/fhir/Patient/{target_id}",
        data=json.dumps(body),
        content_type="application/fhir+json",
        headers=headers,
    )


@when(
    parsers.parse(
        '"{who}" updates the patient "{target}" with phone "{phone}" and birth date "{born}"'
        " at the {which} version"
    )
)
def updates_patient(
    patients: Patients,
    exchange: Exchange,
    who: str,
    target: str,
    phone: str,
    born: str,
    which: str,
) -> None:
    body = _resource(patients, target, phone=phone, birthDate=born)
    version = patients.version if which == "current" else patients.previous
    _put(exchange, _who(patients, who), patients.ids()[target], body, version)


@when(parsers.parse('"{who}" changes the {field} of the patient "{target}" to "{value}"'))
def changes_field(
    patients: Patients, exchange: Exchange, who: str, field: str, target: str, value: str
) -> None:
    body = _resource(patients, target, **{field: value})
    _put(exchange, _who(patients, who), patients.ids()[target], body, patients.version)


@when(parsers.parse('a client without a token updates the patient "{target}"'))
def updates_without_token(patients: Patients, exchange: Exchange, target: str) -> None:
    body = _resource(patients, target)
    _put(exchange, None, patients.ids()[target], body, patients.version)


@when(parsers.parse('"{who}" saves phone "{phone}" and birth date "{born}" on the profile screen'))
def saves_profile_screen(patients: Patients, who: str, phone: str, born: str) -> None:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(patients.people[who])
    response = client.post(PROFILE_URL, {"phone": phone, "birth_date": born})
    assert response.status_code == 302, response.content


@then(
    parsers.parse(
        'the patient "{target}" is shown with their name, birth date, email, phone and status'
    )
)
def patient_shown(patients: Patients, exchange: Exchange, target: str) -> None:
    body = exchange.body()
    user = patients.people[target]
    assert exchange.response.status_code == 200, body
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    assert (body["resourceType"], body["id"]) == ("Patient", str(user.id))
    assert body["name"] == [{"text": user.full_name}]
    assert body["birthDate"] == str(user.birth_date)
    assert body["telecom"] == [
        {"system": "email", "value": user.email.value},
        {"system": "phone", "value": user.phone},
    ]
    assert body["active"] is True


@then("no FHIR patient is found")
def no_patient_found(patients: Patients, exchange: Exchange) -> None:
    patients_found(patients, exchange, "")


@then(parsers.parse('the FHIR patients found are "{names}"'))
def patients_found(patients: Patients, exchange: Exchange, names: str) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    by_id = {str(u.id): name for name, u in patients.people.items()}
    found = [by_id[e["resource"]["id"]] for e in body.get("entry", [])]
    assert ", ".join(found) == names
    assert body["total"] == len(found)


@then("the update answers 200 with a new version")
def updated(patients: Patients, exchange: Exchange) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert body["meta"]["versionId"] != patients.version
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'


@then(parsers.parse('the patient "{target}" has phone "{phone}" and birth date "{born}"'))
def stored_profile(patients: Patients, target: str, phone: str, born: str) -> None:
    user = DjangoUsers().get(patients.people[target].id)
    assert user is not None
    assert (user.phone, str(user.birth_date)) == (phone, born)


@then(parsers.parse('the refusal names the field "{path}"'))
def refusal_field(exchange: Exchange, path: str) -> None:
    assert exchange.body()["issue"][0]["expression"] == [path]


@then(parsers.parse('the "{first}" and "{second}" entries "{action}" are alike but for the actor'))
def alike_entries(patients: Patients, first: str, second: str, action: str) -> None:
    def entry(who: str) -> dict[str, Any]:
        user_id = patients.people[who].id.value
        (found,) = AuditEntryRecord.objects.filter(action=action, entity_id=user_id).values(
            "actor_id", "entity_type", "entity_id", "metadata"
        )
        assert found.pop("actor_id") == found.pop("entity_id") == user_id
        return found

    assert entry(first) == entry(second)
