import json

from django.http import HttpResponse

from drlibre.interfaces.fhir.schemas.common import CodeableConcept, Coding
from drlibre.interfaces.fhir.schemas.outcome import OperationOutcome, OperationOutcomeIssue
from drlibre.shared_kernel.errors import DomainError, ErrorCode

FHIR_JSON = "application/fhir+json; charset=utf-8"
ERROR_CODES = "urn:drlibre:error-code"

# FHIR issue type of each product code (R4 IssueType value set).
_ISSUE_TYPE = {
    ErrorCode.INVALID_INPUT: "invalid",
    ErrorCode.UNAUTHENTICATED: "login",
    ErrorCode.FORBIDDEN: "forbidden",
    ErrorCode.NOT_FOUND: "not-found",
    ErrorCode.CONFLICT: "conflict",
    ErrorCode.NO_ROOM_AVAILABLE: "conflict",
    ErrorCode.NO_CLINICIAN_AVAILABLE: "conflict",
    ErrorCode.HAS_DEPENDENTS: "conflict",
    ErrorCode.INVALID_TRANSITION: "business-rule",
    ErrorCode.RULE_VIOLATION: "business-rule",
}


def fhir_response(body: str, *, status: int) -> HttpResponse:
    return HttpResponse(body, status=status, content_type=FHIR_JSON)


def _render(outcome: OperationOutcome, *, status: int) -> HttpResponse:
    return fhir_response(outcome.model_dump_json(by_alias=True, exclude_none=True), status=status)


def _fields(details: dict[str, object]) -> tuple[str, ...] | None:
    fields = details.get("fields")
    if not isinstance(fields, list):
        return None
    names = tuple(str(f["field"]) for f in fields if isinstance(f, dict) and "field" in f)
    return names or None


def error_outcome(error: DomainError) -> HttpResponse:
    """A refusal as an OperationOutcome carrying its product code, with its HTTP status."""
    issue = OperationOutcomeIssue(
        severity="error",
        code=_ISSUE_TYPE[error.code],
        details=CodeableConcept(
            coding=(Coding(system=ERROR_CODES, code=error.code.value),), text=error.message
        ),
        diagnostics=json.dumps(error.details, ensure_ascii=False) if error.details else None,
        expression=_fields(error.details),
    )
    response = _render(OperationOutcome(issue=(issue,)), status=error.code.http_status)
    if error.code is ErrorCode.UNAUTHENTICATED:
        response["WWW-Authenticate"] = "Bearer"
    return response


def not_supported(allowed: str) -> HttpResponse:
    """An undeclared interaction: 405, an HTTP refusal outside the product codes."""
    issue = OperationOutcomeIssue(
        severity="error",
        code="not-supported",
        details=CodeableConcept(text="Cette interaction n'est pas prise en charge."),
    )
    response = _render(OperationOutcome(issue=(issue,)), status=405)
    response["Allow"] = allowed
    return response
