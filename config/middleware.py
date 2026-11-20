import re
import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

HEADER = "x-correlation-id"
_VALID = re.compile(r"[\x21-\x7e]{1,128}")
logger = structlog.get_logger("drlibre.request")


def correlation_id_from(raw: str | None) -> str:
    if raw is not None and _VALID.fullmatch(raw):
        return raw
    return str(uuid.uuid4())


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = correlation_id_from(request.headers.get(HEADER))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response[HEADER] = correlation_id
            logger.info(
                "request",
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class SameOriginMiddleware:
    """Refuse state-changing requests sent from another origin, API included (spec 12.3)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method not in _SAFE_METHODS and _is_cross_origin(request):
            return _forbidden(request)
        return self.get_response(request)


def _is_cross_origin(request: HttpRequest) -> bool:
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        return True
    origin = request.headers.get("Origin")
    if origin is None:
        return False
    return origin != f"{request.scheme}://{request.get_host()}"


def _forbidden(request: HttpRequest) -> HttpResponse:
    message = "Requête refusée : elle vient d'un autre site."
    if request.path.startswith("/api/"):
        body = {"code": "forbidden", "message": message, "details": {}}
        return JsonResponse(body, status=403)
    return render(request, "errors/403.html", {"message": message}, status=403)
