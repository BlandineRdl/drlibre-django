from collections.abc import Callable
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect, render

from drlibre.bootstrap import act_as, stop_acting
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity, Role
from drlibre.interfaces.paths import API_PREFIXES, FHIR_PREFIX
from drlibre.shared_kernel.errors import DomainError, ErrorCode

type View = Callable[..., HttpResponseBase]

HOMES = {Role.ADMIN: "/console/", Role.CLINICIAN: "/workspace/", Role.PATIENT: "/portal/"}
FORCED_CHANGE_PAGE = "/account/password"
_ATTR = "drlibre_identity"


def identity_of(request: HttpRequest) -> Identity | None:
    return getattr(request, _ATTR, None)


def current_identity(request: HttpRequest) -> Identity:
    """The identity a guarded view runs for; its guard already sent anonymous users away."""
    identity = identity_of(request)
    if identity is None:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "Connectez-vous pour continuer.")
    return identity


def set_session_cookie(response: HttpResponse, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        token,
        expires=expires_at,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
    )


def clear_session_cookie(response: HttpResponse) -> None:
    response.delete_cookie(settings.SESSION_COOKIE_NAME, samesite=settings.SESSION_COOKIE_SAMESITE)


def session_token(request: HttpRequest) -> str | None:
    # FHIR clients authenticate by bearer only, so a cookie there opens no CSRF surface.
    if request.path.startswith(FHIR_PREFIX):
        return None
    return request.COOKIES.get(settings.SESSION_COOKIE_NAME)


def bearer_token(request: HttpRequest) -> str | None:
    # A bearer opens the APIs only, never a web page.
    if not request.path.startswith(API_PREFIXES):
        return None
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return (token.strip() or None) if scheme.lower() == "bearer" else None


class SessionMiddleware:
    """Resolve who holds the bearer token on the APIs, else the session cookie, on every request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        bearer = bearer_token(request)
        if bearer:
            return self._respond(request, container().authenticate_token.execute(token=bearer))
        token = session_token(request)
        identity = container().authenticate_session.execute(token=token) if token else None
        response = self._respond(request, identity)
        if token and identity is None and settings.SESSION_COOKIE_NAME not in response.cookies:
            clear_session_cookie(response)
        elif token and identity and identity.session_renewed:
            set_session_cookie(response, token, identity.session_expires_at)
        return response

    def _respond(self, request: HttpRequest, identity: Identity | None) -> HttpResponse:
        setattr(request, _ATTR, identity)
        acting = act_as(identity.user_id.value if identity else None)
        try:
            return self.get_response(request)
        finally:
            stop_acting(acting)


def forbidden_page(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/403.html", status=403)


def to_sign_in(request: HttpRequest) -> HttpResponse:
    return redirect(f"/sign-in?{urlencode({'next': request.get_full_path()})}")


def require_role(role: Role) -> Callable[[View], View]:
    """No session → sign-in; another role → forbidden; a forced password change comes first."""

    def decorate(view: View) -> View:
        @wraps(view)
        def guarded(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
            identity = identity_of(request)
            if identity is None:
                return to_sign_in(request)
            if identity.role is not role:
                return forbidden_page(request)
            if identity.must_change_password:
                return redirect(FORCED_CHANGE_PAGE)
            return view(request, *args, **kwargs)

        return guarded

    return decorate


def require_password_holder(view: View) -> View:
    @wraps(view)
    def guarded(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        identity = identity_of(request)
        if identity is None:
            return to_sign_in(request)
        if not identity.has_password:
            return forbidden_page(request)
        return view(request, *args, **kwargs)

    return guarded
