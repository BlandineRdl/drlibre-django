from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import ValidationError

from drlibre.interfaces.api.auth import router as auth_router
from drlibre.interfaces.api.health import router as health_router
from drlibre.shared_kernel.errors import DomainError, ErrorCode

api = NinjaAPI(title="DrLibre API", version="1", urls_namespace="api-v1")
api.add_router("/", health_router)
api.add_router("/", auth_router)


@api.exception_handler(DomainError)
def domain_error(request: HttpRequest, error: DomainError) -> HttpResponse:
    body = {"code": error.code.value, "message": error.message, "details": error.details}
    return api.create_response(request, body, status=error.code.http_status)


@api.exception_handler(ValidationError)
def invalid_payload(request: HttpRequest, error: ValidationError) -> HttpResponse:
    fields = [{"field": str(e["loc"][-1]), "message": e["msg"]} for e in error.errors]
    return domain_error(
        request, DomainError(ErrorCode.INVALID_INPUT, "Requête invalide.", {"fields": fields})
    )
