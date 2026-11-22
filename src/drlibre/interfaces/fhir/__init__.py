from functools import wraps
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.urls import URLPattern, re_path
from ninja import NinjaAPI
from ninja.errors import ValidationError
from ninja.parser import Parser
from ninja.renderers import JSONRenderer

from drlibre.interfaces.fhir.access import gate
from drlibre.interfaces.fhir.metadata import router as metadata_router
from drlibre.interfaces.fhir.outcome import error_outcome, not_supported
from drlibre.interfaces.fhir.routers.appointment_responses import (
    router as appointment_responses_router,
)
from drlibre.interfaces.fhir.routers.appointments import router as appointments_router
from drlibre.interfaces.fhir.routers.audit_events import router as audit_events_router
from drlibre.interfaces.fhir.routers.communications import router as communications_router
from drlibre.interfaces.fhir.routers.patients import router as patients_router
from drlibre.interfaces.fhir.routers.reference_writes import router as directory_router
from drlibre.interfaces.fhir.routers.slots import router as slots_router
from drlibre.interfaces.fhir.routing import require_fhir_json
from drlibre.shared_kernel.errors import DomainError, ErrorCode


class FhirRenderer(JSONRenderer):
    media_type = "application/fhir+json"


class FhirParser(Parser):
    def parse_body(self, request: HttpRequest) -> dict[str, Any]:
        require_fhir_json(request)
        return super().parse_body(request)


fhir = NinjaAPI(
    title="DrLibre FHIR R4",
    version="4.0.1",
    urls_namespace="fhir",
    renderer=FhirRenderer(),
    parser=FhirParser(),
    auth=gate,
    docs_url=None,
    openapi_url=None,
)
fhir.add_router("/", metadata_router)
fhir.add_router("/", directory_router)
fhir.add_router("/", slots_router)
fhir.add_router("/", patients_router)
fhir.add_router("/", appointments_router)
fhir.add_router("/", appointment_responses_router)
fhir.add_router("/", communications_router)
fhir.add_router("/", audit_events_router)


@fhir.exception_handler(DomainError)
def domain_error(request: HttpRequest, error: DomainError) -> HttpResponse:
    return error_outcome(error)


@fhir.exception_handler(ValidationError)
def invalid_payload(request: HttpRequest, error: ValidationError) -> HttpResponse:
    fields = [
        {"field": ".".join(map(str, e["loc"][1:])), "message": e["msg"]} for e in error.errors
    ]
    details = {"fields": fields}
    return error_outcome(DomainError(ErrorCode.INVALID_INPUT, "Ressource invalide.", details))


@fhir.exception_handler(Http404)
def unknown(request: HttpRequest, error: Http404) -> HttpResponse:
    return error_outcome(DomainError(ErrorCode.NOT_FOUND, "Ressource introuvable."))


def _outcome_when_not_allowed(view: Any) -> Any:
    @wraps(view)
    def guarded(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        response = view(request, *args, **kwargs)
        if response.status_code == 405:
            return not_supported(response["Allow"])
        return response

    return guarded


def unknown_path(request: HttpRequest, path: str) -> HttpResponse:
    return error_outcome(DomainError(ErrorCode.NOT_FOUND, "Ressource introuvable."))


def urls() -> tuple[list[URLPattern], str, str]:
    """Ninja's routes, a bare 405 or an unknown path made an OperationOutcome."""
    patterns, app_name, namespace = fhir.urls
    wrapped = []
    for p in patterns:
        if not isinstance(p, URLPattern):
            raise TypeError(f"unexpected FHIR route {p!r}")
        wrapped.append(
            URLPattern(p.pattern, _outcome_when_not_allowed(p.callback), p.default_args, p.name)
        )
    wrapped.append(re_path(r"^(?P<path>.*)$", unknown_path))
    return wrapped, app_name, namespace
