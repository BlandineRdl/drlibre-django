from typing import Literal

from django.http import HttpRequest
from ninja import Router

from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.params import refuse_undeclared
from drlibre.interfaces.fhir.registry import ResourceRules, declared
from drlibre.interfaces.fhir.schemas.common import (
    CodeableConcept,
    Coding,
    DomainResource,
    FhirModel,
)

router = Router(tags=["metadata"])

RELEASED = "2026-11-22"
SECURITY = "http://terminology.hl7.org/CodeSystem/restful-security-service"


class Interaction(FhirModel):
    code: str


class SearchParam(FhirModel):
    name: str
    type: str
    documentation: str | None = None


class Resource(FhirModel):
    type: str
    interaction: tuple[Interaction, ...]
    search_param: tuple[SearchParam, ...] | None = None
    search_include: tuple[str, ...] | None = None


class Security(FhirModel):
    service: tuple[CodeableConcept, ...]
    description: str


class Rest(FhirModel):
    mode: Literal["server"] = "server"
    security: Security
    resource: tuple[Resource, ...]


class Implementation(FhirModel):
    description: str
    url: str


class CapabilityStatement(DomainResource):
    resource_type: Literal["CapabilityStatement"] = "CapabilityStatement"
    status: Literal["active"] = "active"
    date: str = RELEASED
    kind: Literal["instance"] = "instance"
    fhir_version: Literal["4.0.1"] = "4.0.1"
    format: tuple[str, ...] = ("application/fhir+json", "json")
    implementation: Implementation
    rest: tuple[Rest, ...]


def _resource(rules: ResourceRules) -> Resource:
    params = [SearchParam(name=p.name, type=p.type.value) for p in rules.search]
    if rules.sorts:
        order = ", ".join(rules.sorts)
        params.append(SearchParam(name="_sort", type="string", documentation=f"{order}, - first"))
    return Resource(
        type=rules.type,
        interaction=tuple(Interaction(code=i.value) for i in rules.interactions),
        search_param=tuple(params) or None,
        search_include=rules.includes or None,
    )


def capability_statement() -> CapabilityStatement:
    """What this server serves, read from the registry, so it declares nothing more or less."""
    bearer = CodeableConcept(coding=(Coding(system=SECURITY, code="OAuth"),), text="Bearer")
    security = Security(service=(bearer,), description="Authorization: Bearer <jeton>")
    return CapabilityStatement(
        implementation=Implementation(description="DrLibre FHIR R4", url=base_url()),
        rest=(Rest(security=security, resource=tuple(map(_resource, declared()))),),
    )


@router.get("/metadata", response=CapabilityStatement, by_alias=True, exclude_none=True)
def metadata(request: HttpRequest) -> CapabilityStatement:
    refuse_undeclared(request.GET, frozenset())
    return capability_statement()
