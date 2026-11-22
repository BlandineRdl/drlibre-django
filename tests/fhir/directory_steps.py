"""Steps of the FHIR reference directory scenarios, on PostgreSQL, shared by their feature files."""

from dataclasses import dataclass
from string import Template
from typing import Any
from urllib.parse import urlsplit

import pytest
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.identity.domain.user import User
from drlibre.interfaces.fhir.mappers.directory import code_system_url, extension_url
from drlibre.shared_kernel.ids import Id
from tests.fhir.conftest import token_for
from tests.fhir.directory_scene import Directory, a_directory, django_repos


@dataclass
class Exchange:
    """The directory a client reads and the last FHIR answer it got."""

    directory: Directory | None = None
    response: Any = None
    previous: Any = None

    def path(self, raw: str) -> str:
        assert self.directory is not None
        return Template(raw).substitute(self.directory.ids())

    def body(self) -> Any:
        return self.response.json()


@pytest.fixture
def exchange() -> Exchange:
    return Exchange()


def _send(exchange: Exchange, path: str, user: User | None = None) -> None:
    headers = {"Authorization": f"Bearer {token_for(user)}"} if user else {}
    exchange.response = Client().get(exchange.path(path), headers=headers)


@given(
    "a reference directory of active and closed hospitals, their departments, rooms, types,"
    " specialties and clinicians"
)
def reference_directory(exchange: Exchange) -> None:
    exchange.directory = a_directory(django_repos())


@when(parsers.parse('a client without a token reads "{path}"'))
@when(parsers.parse('a client without a token searches "{path}"'))
def reads_without_token(exchange: Exchange, path: str) -> None:
    _send(exchange, path)


@when(parsers.parse('the client with the "{who}" token reads "{path}"'))
@when(parsers.parse('the client with the "{who}" token searches "{path}"'))
def reads_with_token(exchange: Exchange, who: str, path: str) -> None:
    assert exchange.directory is not None
    _send(exchange, path, getattr(exchange.directory, who))


@when(parsers.parse('the client follows the "{relation}" link'))
def follows(exchange: Exchange, relation: str) -> None:
    (url,) = [link["url"] for link in exchange.body()["link"] if link["relation"] == relation]
    parts = urlsplit(url)
    exchange.response = Client().get(f"{parts.path}?{parts.query}")


@then(parsers.parse('the answer is a FHIR "{resource}" with the id of "{record}"'))
def is_resource(exchange: Exchange, resource: str, record: str) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert exchange.response["Content-Type"] == "application/fhir+json; charset=utf-8"
    assert (body["resourceType"], body["id"]) == (resource, exchange.path(f"${record}"))


@then("it carries a version, its last update and the version as ETag")
def is_versioned(exchange: Exchange) -> None:
    found = exchange.body()["meta"]
    assert found["versionId"]
    assert found["lastUpdated"]
    assert exchange.response["ETag"] == f'W/"{found["versionId"]}"'


@then(parsers.parse('the organization is of type "{code}" and part of "{parent}"'))
@then(parsers.parse('the organization is of type "{code}"'))
def organization_type(exchange: Exchange, code: str, parent: str | None = None) -> None:
    body = exchange.body()
    assert body["type"][0]["coding"][0]["code"] == code
    assert body.get("partOf", {}).get("reference") == (parent and exchange.path(parent))


@then(
    parsers.parse(
        'the site shows its address in "{city}", its phone, its position and the time zone "{zone}"'
    )
)
def site_details(exchange: Exchange, city: str, zone: str) -> None:
    body = exchange.body()
    assert body["address"]["city"] == city
    assert body["telecom"] == [{"system": "phone", "value": "+33 3 20 00 00 00"}]
    assert body["position"] == {"longitude": 3.06, "latitude": 50.63}
    assert {"url": extension_url("time-zone"), "valueCode": zone} in body["extension"]


@then(parsers.parse('the room is part of "{site}"'))
def room_part_of(exchange: Exchange, site: str) -> None:
    body = exchange.body()
    assert body["physicalType"]["coding"][0]["code"] == "ro"
    assert body["partOf"]["reference"] == exchange.path(site)


def _matches(exchange: Exchange) -> list[tuple[str, str]]:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert (body["resourceType"], body["type"]) == ("Bundle", "searchset")
    return [
        (e["resource"]["resourceType"], e["resource"]["id"])
        for e in body.get("entry", [])
        if e["search"]["mode"] == "match"
    ]


@then(parsers.parse('the bundle holds only "{resource}" "{records}"'))
@then(parsers.parse('the bundle matches "{resource}" "{records}"'))
def bundle_holds(exchange: Exchange, resource: str, records: str) -> None:
    named = [] if records == "none" else records.split(",")
    wanted = [(resource, exchange.path(r.strip())) for r in named]
    assert _matches(exchange) == wanted
    assert exchange.body()["total"] == len(wanted)


@then(parsers.parse('the bundle includes "{first}" "{first_id}" and "{second}" "{second_id}"'))
def bundle_includes(
    exchange: Exchange, first: str, first_id: str, second: str, second_id: str
) -> None:
    included = {
        (e["resource"]["resourceType"], e["resource"]["id"])
        for e in exchange.body()["entry"]
        if e["search"]["mode"] == "include"
    }
    assert included == {(first, exchange.path(first_id)), (second, exchange.path(second_id))}


@then(parsers.parse('the value set gathers the code system of "{record}" only'))
def value_set(exchange: Exchange, record: str) -> None:
    body = exchange.body()
    assert (body["resourceType"], body["id"]) == ("ValueSet", "specialties")
    systems = [i["system"] for i in body["compose"]["include"]]
    assert systems == [code_system_url(Id.parse(exchange.path(record)))]


@then(
    parsers.parse(
        'the searchset has a total of {total:d}, the links "{links}" and the entries "{names}"'
    )
)
def searchset(exchange: Exchange, total: int, links: str, names: str) -> None:
    body = exchange.body()
    assert body["total"] == total
    assert [link["relation"] for link in body["link"]] == links.split(", ")
    assert [e["resource"]["name"] for e in body["entry"]] == names.split(", ")


@then(parsers.parse('the practitioner shows "{name}" titled "{title}" without email or phone'))
def public_practitioner(exchange: Exchange, name: str, title: str) -> None:
    body = exchange.body()
    assert body["name"] == [{"text": name, "prefix": [title]}]
    assert "telecom" not in body


@then(parsers.parse('the practitioner shows the email and phone of "{who}"'))
def staff_practitioner(exchange: Exchange, who: str) -> None:
    user = getattr(exchange.directory, who)
    assert exchange.body()["telecom"] == [
        {"system": "email", "value": user.email.value},
        {"system": "phone", "value": user.phone},
    ]


@then(parsers.parse('the role shows the round robin weight {weight:d} and the reason "{reason}"'))
def staff_role(exchange: Exchange, weight: int, reason: str) -> None:
    body = exchange.body()
    assert {"url": extension_url("round-robin-weight"), "valueInteger": weight} in body["extension"]
    assert [n["description"] for n in body["notAvailable"]] == [reason]
    assert len(body["healthcareService"]) == 2


@then("the role hides the round robin weight, the reason and the types booked offline")
def public_role(exchange: Exchange) -> None:
    body = exchange.body()
    assert all(e["url"] != extension_url("round-robin-weight") for e in body["extension"])
    assert [n["description"] for n in body["notAvailable"]] == ["Indisponible"]
    assert len(body["healthcareService"]) == 1


@then(parsers.parse('the role is coded "{code}" for "Practitioner/{who}"'))
def admin_role(exchange: Exchange, code: str, who: str) -> None:
    body = exchange.body()
    assert body["code"][0]["coding"][0]["code"] == code
    assert body["practitioner"]["reference"] == exchange.path(f"Practitioner/{who}")


@then(
    parsers.parse(
        'the answer is {status:d} with an OperationOutcome "{issue}" and the code "{code}"'
    )
)
def outcome(exchange: Exchange, status: int, issue: str, code: str) -> None:
    body = exchange.body()
    assert exchange.response.status_code == status, body
    assert exchange.response["Content-Type"].startswith("application/fhir+json")
    (found,) = body["issue"]
    assert (found["code"], found["details"]["coding"][0]["code"]) == (issue, code)


@then(parsers.parse('the client is refused with {status:d} and the code "{code}"'))
def refused(exchange: Exchange, status: int, code: str) -> None:
    assert exchange.response.status_code == status
    assert exchange.body()["issue"][0]["details"]["coding"][0]["code"] == code
