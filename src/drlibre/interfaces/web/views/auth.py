from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.auth import (
    HOMES,
    clear_session_cookie,
    current_identity,
    identity_of,
    require_password_holder,
    session_token,
    set_session_cookie,
)
from drlibre.interfaces.web.presenters.auth import password_form, sign_in_form
from drlibre.shared_kernel.errors import DomainError


@require_http_methods(["GET"])
def home(request: HttpRequest) -> HttpResponse:
    identity = identity_of(request)
    return redirect(HOMES[identity.role] if identity else "/sign-in")


def _safe_next(request: HttpRequest, raw: str, home_path: str) -> str:
    allowed = url_has_allowed_host_and_scheme(raw, allowed_hosts={request.get_host()})
    return raw if allowed and raw.startswith(home_path) else home_path


@require_http_methods(["GET", "POST"])
def sign_in(request: HttpRequest) -> HttpResponse:
    next_url = request.POST.get("next") or request.GET.get("next", "")
    context: dict[str, object] = {"hidden_fields": [("next", next_url)] if next_url else []}
    if request.method == "GET":
        return render(request, "auth/form_page.html", {**context, "form": sign_in_form({})})
    try:
        signed = container().sign_in.execute(
            email=request.POST.get("email", ""),
            password=request.POST.get("password", ""),
            user_agent=request.headers.get("User-Agent", ""),
        )
    except DomainError as error:
        form = sign_in_form({"email": request.POST.get("email", "")}, error)
        return render(
            request, "auth/form_page.html", {**context, "form": form}, status=error.code.http_status
        )
    response = redirect(_safe_next(request, next_url, HOMES[signed.role]))
    set_session_cookie(response, signed.token, signed.expires_at)
    return response


@require_POST
def sign_out(request: HttpRequest) -> HttpResponse:
    token = session_token(request)
    if token:
        container().sign_out.execute(token=token)
    response = redirect("/sign-in")
    clear_session_cookie(response)
    return response


@require_password_holder
@require_http_methods(["GET", "POST"])
def change_password(request: HttpRequest) -> HttpResponse:
    identity = current_identity(request)
    forced = identity.must_change_password
    intro = (
        "Votre mot de passe est temporaire : choisissez le vôtre pour continuer." if forced else ""
    )
    if request.method == "GET":
        form = password_form(forced=forced)
        return render(request, "auth/form_page.html", {"form": form, "intro": intro})
    try:
        container().change_password.execute(
            user_id=identity.user_id,
            current_password=request.POST.get("current_password", ""),
            new_password=request.POST.get("new_password", ""),
        )
    except DomainError as error:
        form = password_form(forced=forced, error=error)
        context = {"form": form, "intro": intro}
        return render(request, "auth/form_page.html", context, status=error.code.http_status)
    return redirect(HOMES[identity.role])
