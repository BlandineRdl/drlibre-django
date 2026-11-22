from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    Address,
    CodeableConcept,
    ContactPoint,
    DomainResource,
    Extension,
    FhirModel,
    HumanName,
    Identifier,
    Meta,
    Period,
    Reference,
)


class Organization(DomainResource):
    resource_type: Literal["Organization"] = "Organization"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    identifier: tuple[Identifier, ...] | None = None
    active: bool
    type: tuple[CodeableConcept, ...]
    name: str
    telecom: tuple[ContactPoint, ...] | None = None
    address: tuple[Address, ...] | None = None
    part_of: Reference | None = None


class Position(FhirModel):
    longitude: float
    latitude: float


class Location(DomainResource):
    resource_type: Literal["Location"] = "Location"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    identifier: tuple[Identifier, ...] | None = None
    status: Literal["active", "inactive"]
    name: str
    description: str | None = None
    physical_type: CodeableConcept
    telecom: tuple[ContactPoint, ...] | None = None
    address: Address | None = None
    position: Position | None = None
    managing_organization: Reference | None = None
    part_of: Reference | None = None


class HealthcareService(DomainResource):
    resource_type: Literal["HealthcareService"] = "HealthcareService"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    identifier: tuple[Identifier, ...] | None = None
    active: bool
    provided_by: Reference
    specialty: tuple[CodeableConcept, ...] | None = None
    name: str


class Concept(FhirModel):
    code: str
    display: str


class CodeSystem(DomainResource):
    resource_type: Literal["CodeSystem"] = "CodeSystem"
    id: str | None = None
    meta: Meta | None = None
    url: str | None = None
    identifier: tuple[Identifier, ...] | None = None
    name: str
    title: str
    status: Literal["active", "retired"]
    content: Literal["complete"] = "complete"
    concept: tuple[Concept, ...]


class ValueSetConcept(FhirModel):
    code: str


class ValueSetInclude(FhirModel):
    system: str | None = None
    concept: tuple[ValueSetConcept, ...]


class ValueSetCompose(FhirModel):
    include: tuple[ValueSetInclude, ...]


class ValueSet(DomainResource):
    resource_type: Literal["ValueSet"] = "ValueSet"
    id: str | None = None
    meta: Meta | None = None
    url: str | None = None
    identifier: tuple[Identifier, ...] | None = None
    name: str
    title: str
    status: Literal["active", "retired"]
    compose: ValueSetCompose


class Practitioner(DomainResource):
    resource_type: Literal["Practitioner"] = "Practitioner"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    active: bool
    name: tuple[HumanName, ...]
    telecom: tuple[ContactPoint, ...] | None = None


class AvailableTime(FhirModel):
    days_of_week: tuple[str, ...]
    available_start_time: str
    available_end_time: str


class NotAvailable(FhirModel):
    description: str
    during: Period


class PractitionerRole(DomainResource):
    resource_type: Literal["PractitionerRole"] = "PractitionerRole"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    active: bool
    practitioner: Reference
    organization: Reference | None = None
    code: tuple[CodeableConcept, ...] | None = None
    specialty: tuple[CodeableConcept, ...] | None = None
    location: tuple[Reference, ...] | None = None
    healthcare_service: tuple[Reference, ...] | None = None
    available_time: tuple[AvailableTime, ...] | None = None
    not_available: tuple[NotAvailable, ...] | None = None


class Schedule(DomainResource):
    """A client writes it without id, meta, `active` or the horizon, all computed."""

    resource_type: Literal["Schedule"] = "Schedule"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    active: bool | None = None
    actor: tuple[Reference, ...]
    planning_horizon: Period | None = None
