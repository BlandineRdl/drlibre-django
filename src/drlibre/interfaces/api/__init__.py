from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

from drlibre.interfaces.api.health import router as health_router
from drlibre.shared_kernel.errors import DomainError

api = NinjaAPI(title="DrLibre API", version="1", urls_namespace="api-v1")
api.add_router("/", health_router)


@api.exception_handler(DomainError)
def domain_error(request: HttpRequest, error: DomainError) -> HttpResponse:
    body = {"code": error.code.value, "message": error.message, "details": error.details}
    return api.create_response(request, body, status=error.code.http_status)
