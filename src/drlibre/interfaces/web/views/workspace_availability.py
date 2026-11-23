import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import require_role
from drlibre.interfaces.web.forms.base import WebForm
from drlibre.interfaces.web.forms.workspace import RuleForm, TimeOffForm
from drlibre.interfaces.web.presenters.availability import (
    RULES_URL,
    TIME_OFF_URL,
    rule_values,
    rules_view,
    time_off_label,
    time_offs_view,
)
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.reference import confirm_view
from drlibre.interfaces.web.views.workspace import Me, current_me, owned, workspace_page
from drlibre.scheduling.application.ports.inbound import AvailabilityRule
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

INVALID = ErrorCode.INVALID_INPUT.http_status


def _rooms(me: Me) -> tuple[tuple[str, str], ...]:
    rooms = container().reference_queries.department_rooms(me.department_id)
    return tuple((str(room.id), room.label) for room in rooms if room.active)


def _form(
    request: HttpRequest,
    me: Me,
    form: WebForm,
    *,
    title: str,
    cancel_url: str,
    status: int = 200,
) -> HttpResponse:
    page = FormPage(title, request.path, "Enregistrer", form, cancel_url=cancel_url)
    return workspace_page(request, "console/form.html", me, {"page": page}, status=status)


def _confirm(request: HttpRequest, me: Me, *, label: str, cancel_url: str) -> HttpResponse:
    confirm = confirm_view(label=label, action=request.path, cancel_url=cancel_url)
    return workspace_page(request, "console/confirm_delete.html", me, {"confirm": confirm})


@require_GET
@require_role(Role.CLINICIAN)
def list_rules(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    rules = container().availability_queries.rules_of(me.profile_id)
    department_rooms = container().reference_queries.department_rooms(me.department_id)
    rooms = {room.id: room.label for room in department_rooms}
    view = rules_view(
        rules, time_zone=me.time_zone, room_labels=rooms, done=request.GET.get("done")
    )
    return workspace_page(request, "workspace/availability.html", me, {"view": view})


def _save_rule(
    request: HttpRequest, me: Me, *, title: str, rule: AvailabilityRule | None
) -> HttpResponse:
    options = {"time_zone": me.time_zone, "rooms": _rooms(me)}
    if request.method == "GET":
        initial = rule_values(rule) if rule else {"step_minutes": "15"}
        return _form(
            request, me, RuleForm(initial=initial, **options), title=title, cancel_url=RULES_URL
        )
    form = RuleForm(request.POST, **options)
    if form.is_valid():
        try:
            container().save_availability_rule.execute(
                actor=me.user_id, rule_id=rule.id if rule else None, fields=form.posted()
            )
        except DomainError as error:
            if error.code is not ErrorCode.INVALID_INPUT:
                raise
            form.refuse(error)
        else:
            return redirect(f"{RULES_URL}?done={'updated' if rule else 'created'}")
    return _form(request, me, form, title=title, cancel_url=RULES_URL, status=INVALID)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def create_rule(request: HttpRequest) -> HttpResponse:
    return _save_rule(request, current_me(request), title="Ajouter une plage", rule=None)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def edit_rule(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = current_me(request)
    rule = owned(container().availability_queries.rule(Id(record_id)), me)
    return _save_rule(request, me, title=f"Modifier la plage « {rule.label} »", rule=rule)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def delete_rule(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = current_me(request)
    rule = owned(container().availability_queries.rule(Id(record_id)), me)
    if request.method == "POST":
        container().delete_availability_rule.execute(actor=me.user_id, rule_id=rule.id)
        return redirect(f"{RULES_URL}?done=deleted")
    return _confirm(request, me, label=rule.label, cancel_url=RULES_URL)


@require_GET
@require_role(Role.CLINICIAN)
def list_time_off(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    found = container().availability_queries.time_offs_of(me.profile_id)
    view = time_offs_view(found, time_zone=me.time_zone, done=request.GET.get("done"))
    return workspace_page(request, "workspace/time_off.html", me, {"view": view})


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def create_time_off(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    title = "Ajouter une absence"
    if request.method == "GET":
        form = TimeOffForm(time_zone=me.time_zone)
        return _form(request, me, form, title=title, cancel_url=TIME_OFF_URL)
    form = TimeOffForm(request.POST, time_zone=me.time_zone)
    if form.is_valid():
        try:
            container().record_time_off.execute(actor=me.user_id, fields=form.posted())
        except DomainError as error:
            if error.code is not ErrorCode.INVALID_INPUT:
                raise
            form.refuse(error)
        else:
            return redirect(f"{TIME_OFF_URL}?done=created")
    return _form(request, me, form, title=title, cancel_url=TIME_OFF_URL, status=INVALID)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def delete_time_off(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = current_me(request)
    found = owned(container().availability_queries.time_off(Id(record_id)), me)
    if request.method == "POST":
        container().delete_time_off.execute(actor=me.user_id, time_off_id=found.id)
        return redirect(f"{TIME_OFF_URL}?done=deleted")
    label = time_off_label(found, me.time_zone)
    return _confirm(request, me, label=label, cancel_url=TIME_OFF_URL)
