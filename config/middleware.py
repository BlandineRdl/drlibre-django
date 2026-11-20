import re
import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

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
