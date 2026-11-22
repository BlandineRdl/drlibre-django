from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    Address,
    CodeableConcept,
    ContactPoint,
    Extension,
    FhirModel,
    HumanName,
    Identifier,
    Meta,
    Period,
    Reference,
)


class Organization(FhirModel):
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


class Location(FhirModel):
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


class HealthcareService(FhirModel):
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


class CodeSystem(FhirModel):
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


class ValueSetInclude(FhirModel):
    system: str


class ValueSetCompose(FhirModel):
    include: tuple[ValueSetInclude, ...]


class ValueSet(FhirModel):
    resource_type: Literal["ValueSet"] = "ValueSet"
    id: str
    meta: Meta
    url: str
    name: str
    title: str
    status: Literal["active"] = "active"
    compose: ValueSetCompose


class Practitioner(FhirModel):
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


class PractitionerRole(FhirModel):
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


class Schedule(FhirModel):
    resource_type: Literal["Schedule"] = "Schedule"
    id: str
    meta: Meta
    extension: tuple[Extension, ...] | None = None
    active: bool
    actor: tuple[Reference, ...]
    planning_horizon: Period
