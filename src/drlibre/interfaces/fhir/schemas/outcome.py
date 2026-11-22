from typing import Literal

from drlibre.interfaces.fhir.schemas.common import CodeableConcept, DomainResource, FhirModel


class OperationOutcomeIssue(FhirModel):
    severity: Literal["fatal", "error", "warning", "information"]
    code: str
    details: CodeableConcept | None = None
    diagnostics: str | None = None
    expression: tuple[str, ...] | None = None


class OperationOutcome(DomainResource):
    resource_type: Literal["OperationOutcome"] = "OperationOutcome"
    issue: tuple[OperationOutcomeIssue, ...]
