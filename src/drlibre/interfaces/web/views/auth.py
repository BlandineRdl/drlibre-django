from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.auth import (
    HOMES,
    clear_session_cookie,
    current_identity,
    require_password_holder,
    session_token,
    set_session_cookie,
)
from drlibre.interfaces.web.forms.auth import LinkRequestForm, PasswordChangeForm, SignInForm
from drlibre.interfaces.web.forms.base import INVALID
from drlibre.interfaces.web.presenters.auth import (
    link_continue,
    link_missing,
    link_refused,
    link_request_page,
    link_sent,
    password_page,
    sign_in_page,
)
from drlibre.shared_kernel.errors import DomainError


def _safe_next(request: HttpRequest, raw: str, home_path: str) -> str:
    allowed = url_has_allowed_host_and_scheme(raw, allowed_hosts={request.get_host()})
    return raw if allowed and raw.startswith(home_path) else home_path


def _sign_in_page(
    request: HttpRequest,
    form: SignInForm,
    link_form: LinkRequestForm,
    next_url: str = "",
    status: int = 200,
) -> HttpResponse:
    context = {
        "page": sign_in_page(form),
        "link_page": link_request_page(link_form),
        "hidden_fields": [("next", next_url)] if next_url else [],
    }
    return render(request, "auth/form_page.html", context, status=status)


@require_http_methods(["GET", "POST"])
def sign_in(request: HttpRequest) -> HttpResponse:
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "GET":
        return _sign_in_page(request, SignInForm(), LinkRequestForm(), next_url)
    form = SignInForm(request.POST)
    if not form.is_valid():
        return _sign_in_page(request, form, LinkRequestForm(), next_url, INVALID)
    try:
        signed = container().sign_in.execute(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            user_agent=request.headers.get("User-Agent", ""),
            network=request.META.get("REMOTE_ADDR", ""),
        )
    except DomainError as error:
        form.refuse(error)
        return _sign_in_page(request, form, LinkRequestForm(), next_url, error.code.http_status)
    response = redirect(_safe_next(request, next_url, HOMES[signed.role]))
    set_session_cookie(response, signed.token, signed.expires_at)
    return response


@require_POST
def request_link(request: HttpRequest) -> HttpResponse:
    form = LinkRequestForm(request.POST)
    if not form.is_valid():
        return _sign_in_page(request, SignInForm(), form, status=INVALID)
    try:
        container().request_sign_in_link.execute(
            email=form.cleaned_data["link_email"], network=request.META.get("REMOTE_ADDR", "")
        )
    except DomainError as error:
        form.refuse(error)
        return _sign_in_page(request, SignInForm(), form, status=error.code.http_status)
    return render(request, "auth/link_sent.html", {"view": link_sent()})


@require_http_methods(["GET", "POST"])
def use_link(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        # Opening the link consumes nothing: only the button on this page does.
        token = request.GET.get("token", "")
        if not token:
            return render(request, "auth/link_continue.html", {"view": link_missing()}, status=401)
        return render(request, "auth/link_continue.html", {"view": link_continue(token)})
    try:
        signed = container().use_sign_in_link.execute(
            token=request.POST.get("token", ""), user_agent=request.headers.get("User-Agent", "")
        )
    except DomainError as error:
        view = link_refused(error)
        return render(request, "auth/link_continue.html", {"view": view}, status=401)
    response = redirect(HOMES[signed.role])
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
        return _password_page(request, PasswordChangeForm(), forced=forced, intro=intro)
    form = PasswordChangeForm(request.POST)
    if not form.is_valid():
        return _password_page(request, form, forced=forced, intro=intro, status=INVALID)
    try:
        container().change_password.execute(
            user_id=identity.user_id,
            current_password=form.cleaned_data["current_password"],
            new_password=form.cleaned_data["new_password"],
        )
    except DomainError as error:
        form.refuse(error)
        status = error.code.http_status
        return _password_page(request, form, forced=forced, intro=intro, status=status)
    return redirect(HOMES[identity.role])


def _password_page(
    request: HttpRequest, form: PasswordChangeForm, *, forced: bool, intro: str, status: int = 200
) -> HttpResponse:
    context = {"page": password_page(form, forced=forced), "intro": intro}
    return render(request, "auth/form_page.html", context, status=status)
