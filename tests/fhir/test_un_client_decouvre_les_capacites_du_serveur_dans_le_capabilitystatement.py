"""Steps of the CapabilityStatement Story: the server serves what metadata declares, only that."""

import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import pytest
from pytest_bdd import parsers, scenarios, then, when

from drlibre.identity.domain.user import Role
from drlibre.interfaces.fhir import fhir, params
from drlibre.interfaces.fhir.params import SearchQuery
from drlibre.interfaces.fhir.registry import Interaction, ResourceRules, declared, declared_routes
from tests.fhir.conftest import Call
from tests.fhir.directory_scene import a_directory, django_repos

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios(
    "../features/fhir/un_client_decouvre_les_capacites_du_serveur_dans_le_capabilitystatement.feature"
)

_SLOT_RANGE = (("start", "ge2026-11-23T00:00:00+01:00"), ("start", "lt2026-11-24T00:00:00+01:00"))


@dataclass
class Capabilities:
    """The answers a client got, and what each search read of its query."""

    response: Any = None
    answers: list[tuple[str, str, Any]] = field(default_factory=list)
    read: dict[str, set[str]] = field(default_factory=dict)


@pytest.fixture
def capabilities() -> Capabilities:
    return Capabilities()


class _Watched(tuple[str, ...]):
    """A query's `_sort` or `_include` values that log every value a handler compares them to."""

    log: set[str]

    def __new__(cls, values: tuple[str, ...], log: set[str]) -> "_Watched":
        made = super().__new__(cls, values)
        made.log = log
        return made

    def __contains__(self, value: object) -> bool:
        self.log.add(str(value))
        return super().__contains__(value)

    def __getitem__(self, index: Any) -> Any:
        found = super().__getitem__(index)
        return _Watched(found, self.log) if isinstance(index, slice) else found

    def __eq__(self, other: object) -> bool:
        self.log.update(map(str, other) if isinstance(other, tuple) else ())
        return tuple(self) == other

    __hash__ = tuple.__hash__


def served_routes() -> set[tuple[str, str]]:
    found = set()
    for bound in fhir._get_bound_routers():
        for path, view in bound.path_operations.items():
            for operation in view.operations:
                full = re.sub(r"/+", "/", f"/{bound.prefix}/{path}")
                normal = re.sub(r"\{[^}]+\}", "{id}", full).rstrip("/")
                found.update((method, normal) for method in operation.methods)
    return found


def _search(rules: ResourceRules, kind: str, extra: tuple[tuple[str, str], ...] = ()) -> str:
    """A search with what it requires: a Slot search names its type and range."""
    required = (("service-type", kind), *_SLOT_RANGE) if rules.type == "Slot" else ()
    return f"/fhir/{rules.type}?{urlencode(required + extra)}"


def _searchable() -> tuple[ResourceRules, ...]:
    return tuple(r for r in declared() if Interaction.SEARCH in r.interactions)


@when("a client without a token reads the capability statement")
def reads_metadata(capabilities: Capabilities, call: Call) -> None:
    capabilities.response = call("GET", "/fhir/metadata")


@then("the answer is a FHIR 4.0.1 CapabilityStatement in application/fhir+json")
def is_capability_statement(capabilities: Capabilities) -> None:
    body = capabilities.response.json()
    assert capabilities.response.status_code == 200
    assert capabilities.response["Content-Type"] == "application/fhir+json; charset=utf-8"
    assert (body["resourceType"], body["fhirVersion"]) == ("CapabilityStatement", "4.0.1")
    assert (body["kind"], body["rest"][0]["mode"]) == ("instance", "server")


@then("each served resource is listed with its interactions, search parameters, includes and sorts")
def lists_resources(capabilities: Capabilities) -> None:
    listed = {r["type"]: r for r in capabilities.response.json()["rest"][0]["resource"]}
    assert set(listed) == {r.type for r in declared()}
    for rules in declared():
        found = listed[rules.type]
        params_of = {p["name"]: p for p in found.get("searchParam", ())}
        assert {i["code"] for i in found["interaction"]} == {i.value for i in rules.interactions}
        assert {n: p["type"] for n, p in params_of.items() if n != "_sort"} == {
            p.name: p.type.value for p in rules.search
        }
        assert set(found.get("searchInclude", ())) == set(rules.includes)
        sorts = params_of.get("_sort", {}).get("documentation", "")
        assert set(re.findall(r"[a-z-]+(?=,)", sorts)) == set(rules.sorts), rules.type


@then("every served route is declared and every declared route is served")
def routes_match() -> None:
    assert served_routes() == declared_routes()


@when("an admin tries every interaction a declared resource does not declare")
def tries_undeclared(capabilities: Capabilities, call: Call, role_token: Any) -> None:
    token = role_token(Role.ADMIN)
    for rules in declared():
        missing = tuple(i for i in Interaction if i not in rules.interactions)
        for method, path in ResourceRules(type=rules.type, interactions=missing).routes():
            sent = path.replace("{id}", str(uuid.uuid4()))
            response = call(
                method, f"/fhir{sent}", token=token, data="{}", content_type="application/fhir+json"
            )
            capabilities.answers.append((method, path, response))


@then("each answers 405 not-supported allowing only the declared methods")
def not_supported(capabilities: Capabilities) -> None:
    assert capabilities.answers
    routes = declared_routes()
    for method, path, response in capabilities.answers:
        allowed = {m for m, p in routes if p == path}
        assert response.status_code == 405, (method, path)
        assert set(response["Allow"].split(", ")) == allowed, (method, path)
        assert response.json()["issue"][0]["code"] == "not-supported"


@when("an admin searches every declared resource")
def searches(
    capabilities: Capabilities, call: Call, role_token: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = role_token(Role.ADMIN)
    kind = str(a_directory(django_repos()).online.id)
    log: set[str] = set()
    listed = params._listed
    values = SearchQuery.values

    def watched_values(query: SearchQuery, name: str) -> tuple[str, ...]:
        log.add(name)
        return values(query, name)

    monkeypatch.setattr(SearchQuery, "values", watched_values)
    monkeypatch.setattr(params, "_listed", lambda *a: _Watched(listed(*a), log))
    for rules in _searchable():
        log.clear()
        response = call("GET", _search(rules, kind), token=token)
        assert response.status_code == 200, (rules.type, response.json())
        capabilities.read[rules.type] = set(log)


@then("each search reads every parameter, include and sort it declares")
def reads_declared(capabilities: Capabilities) -> None:
    assert capabilities.read
    for rules in _searchable():
        expected = {p.name for p in rules.search} | set(rules.includes)
        expected |= {f"-{s}" for s in rules.sorts}
        assert expected <= capabilities.read[rules.type], (rules.type, expected)


@when("an admin searches every declared resource with an undeclared parameter, include or sort")
def searches_undeclared(capabilities: Capabilities, call: Call, role_token: Any) -> None:
    token = role_token(Role.ADMIN)
    kind = str(uuid.uuid4())
    for rules in _searchable():
        for extra in (("unknown", "1"), ("_include", "Patient:link"), ("_sort", "_id")):
            response = call("GET", _search(rules, kind, (extra,)), token=token)
            capabilities.answers.append(("GET", f"{rules.type}?{extra[0]}", response))


@then(parsers.parse('each search is refused with {status:d} and the code "{code}"'))
def refused(capabilities: Capabilities, status: int, code: str) -> None:
    assert capabilities.answers
    for _, asked, response in capabilities.answers:
        body = response.json()
        assert response.status_code == status, asked
        assert body["issue"][0]["details"]["coding"][0]["code"] == code, asked
