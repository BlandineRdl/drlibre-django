from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from drlibre.shared_kernel.errors import DomainError, ErrorCode

_PAGES = {ErrorCode.NOT_FOUND: "errors/404.html", ErrorCode.FORBIDDEN: "errors/403.html"}


def forbidden(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return render(request, "errors/403.html", status=403)


def not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return render(request, "errors/404.html", status=404)


class DomainErrorPagesMiddleware:
    """Render a refusal a web view did not handle as its error page; the API has its own handler."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        if not isinstance(exception, DomainError) or request.path.startswith("/api/"):
            return None
        template = _PAGES.get(exception.code, "errors/403.html")
        context = {"message": exception.message}
        return render(request, template, context, status=exception.code.http_status)
