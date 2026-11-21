import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.waitlist import (
    ADD_FIELDS,
    CONSOLE_WAITLIST_URL,
    console_list,
    join_form,
    join_input,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

# Refusals the list and the add form show inline instead of an error page.
_INLINE = frozenset(
    {
        ErrorCode.INVALID_INPUT,
        ErrorCode.RULE_VIOLATION,
        ErrorCode.INVALID_TRANSITION,
        ErrorCode.CONFLICT,
        ErrorCode.NO_ROOM_AVAILABLE,
    }
)
# A join or a manual offer also shows not_found inline: no patient, type or slot fits.
_INLINE_OR_MISSING = _INLINE | {ErrorCode.NOT_FOUND}


def _list(request: HttpRequest, error: DomainError | None = None) -> HttpResponse:
    data = request.GET if request.method == "GET" else request.POST
    status = data.get("status", "")
    page_request = PageRequest.from_query(page=data.get("page"), search=None)
    c = container()
    view = console_list(
        c.waitlist_queries.page(status, page_request),
        status,
        c.clock.now(),
        notice=request.GET.get("done", ""),
        error=error,
    )
    context = {"view": view, "section_nav": console_nav(CONSOLE_WAITLIST_URL)}
    code = error.code.http_status if error else 200
    return render(request, "console/waitlist.html", context, status=code)


@require_GET
@require_role(Role.ADMIN)
def list_entries(request: HttpRequest) -> HttpResponse:
    return _list(request)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def add_entry(request: HttpRequest) -> HttpResponse:
    values = {spec.name: request.POST.get(spec.name, "") for spec in ADD_FIELDS}
    error: DomainError | None = None
    if request.method == "POST":
        try:
            container().join_waitlist.execute(
                actor_id=current_identity(request).user_id,
                patient_email=values["patient_email"].strip(),
                **join_input(values),
            )
        except DomainError as refused:
            if refused.code not in _INLINE_OR_MISSING:
                raise
            error = refused
        else:
            return redirect(f"{CONSOLE_WAITLIST_URL}?done=added")
    options = container().booking_option_queries
    form = join_form(
        title="Inscrire un patient sur la liste d'attente",
        action=request.path,
        submit_label="Inscrire",
        specs=ADD_FIELDS,
        types=options.type_options(online_only=False),
        clinicians=options.clinician_options(),
        values=values,
        error=error,
        cancel_url=CONSOLE_WAITLIST_URL,
    )
    context = {"form": form, "section_nav": console_nav(request.path)}
    code = error.code.http_status if error else 200
    return render(request, "console/form.html", context, status=code)


@require_POST
@require_role(Role.ADMIN)
def offer(request: HttpRequest, entry_id: uuid.UUID) -> HttpResponse:
    try:
        container().offer_cancelled_slot.execute(
            actor_id=current_identity(request).user_id, entry_id=Id(entry_id)
        )
    except DomainError as error:
        if error.code not in _INLINE_OR_MISSING:
            raise
        return _list(request, error)
    return redirect(f"{CONSOLE_WAITLIST_URL}?done=offered")


@require_POST
@require_role(Role.ADMIN)
def accept(request: HttpRequest, entry_id: uuid.UUID) -> HttpResponse:
    try:
        container().accept_waitlist_offer.execute(
            actor_id=current_identity(request).user_id, entry_id=Id(entry_id)
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        return _list(request, error)
    return redirect(f"{CONSOLE_WAITLIST_URL}?done=booked")
