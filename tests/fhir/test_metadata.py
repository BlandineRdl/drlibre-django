import re

import pytest

from drlibre.interfaces.fhir import fhir
from drlibre.interfaces.fhir.registry import declared, declared_routes
from tests.fhir.conftest import Call


def served_routes() -> set[tuple[str, str]]:
    found = set()
    for bound in fhir._get_bound_routers():
        for path, view in bound.path_operations.items():
            for operation in view.operations:
                full = re.sub(r"/+", "/", f"/{bound.prefix}/{path}")
                normal = re.sub(r"\{[^}]+\}", "{id}", full).rstrip("/")
                found.update((method, normal) for method in operation.methods)
    return found


def test_the_capability_statement_is_fhir_r4_json_without_a_token(call: Call) -> None:
    """Spec §15.1: GET /fhir/metadata, served as application/fhir+json, FHIR 4.0.1."""
    response = call("GET", "/fhir/metadata")

    body = response.json()
    assert response.status_code == 200
    assert response["Content-Type"] == "application/fhir+json; charset=utf-8"
    assert body["resourceType"] == "CapabilityStatement"
    assert body["fhirVersion"] == "4.0.1"
    assert body["kind"] == "instance"
    assert body["rest"][0]["mode"] == "server"


def test_the_capability_statement_lists_exactly_the_declared_interactions(call: Call) -> None:
    """Story CapabilityStatement: it declares nothing it does not serve."""
    body = call("GET", "/fhir/metadata").json()

    listed = {r["type"]: {i["code"] for i in r["interaction"]} for r in body["rest"][0]["resource"]}
    assert listed == {r.type: {i.value for i in r.interactions} for r in declared()}


def test_every_served_route_is_declared_and_every_declared_route_is_served() -> None:
    """Story CapabilityStatement: it serves nothing it does not declare, and the reverse."""
    assert served_routes() == declared_routes()


@pytest.mark.parametrize("method", ["DELETE", "POST", "PUT"])
def test_an_undeclared_interaction_is_refused_as_not_supported(call: Call, method: str) -> None:
    """Spec §15.1: an interaction the server does not declare answers 405 not-supported."""
    response = call(method, "/fhir/metadata")

    body = response.json()
    assert response.status_code == 405
    assert response["Allow"] == "GET"
    assert response["Content-Type"].startswith("application/fhir+json")
    assert body["issue"][0]["code"] == "not-supported"
