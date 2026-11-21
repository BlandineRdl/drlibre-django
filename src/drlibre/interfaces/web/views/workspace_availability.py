import uuid
from collections.abc import Mapping
from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.availability import (
    RULES_URL,
    TIME_OFF_URL,
    WEEKDAY_CHOICES,
    rule_fields,
    rule_values,
    rules_view,
    time_off_fields,
    time_off_label,
    time_offs_view,
)
from drlibre.interfaces.web.presenters.forms import Choice, FieldSpec, build_form
from drlibre.interfaces.web.presenters.reference import confirm_view
from drlibre.interfaces.web.time_zones import hospital_time_zone
from drlibre.scheduling.application.ports.inbound import AvailabilityRule, TimeOff
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Me:
    user_id: Id
    profile_id: Id
    department_id: Id
    time_zone: str


def _me(request: HttpRequest) -> Me:
    user_id = current_identity(request).user_id
    profile = container().reference_queries.clinician_profile_of(user_id)
    if profile is None:
        raise DomainError(ErrorCode.FORBIDDEN, "Réservé aux praticiens ayant un profil.")
    return Me(user_id, profile.id, profile.department_id, hospital_time_zone(profile.department_id))


def _owned[T: (AvailabilityRule, TimeOff)](found: T | None, me: Me) -> T:
    if found is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.")
    if found.clinician_id != me.profile_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Cet élément appartient à un autre praticien.")
    return found


def _rooms(me: Me) -> tuple[Choice, ...]:
    rooms = container().reference_queries.department_rooms(me.department_id)
    return tuple(Choice(str(room.id), room.label) for room in rooms if room.active)


def _page(
    request: HttpRequest, template: str, me: Me, context: Mapping[str, object], *, status: int = 200
) -> HttpResponse:
    # The footer and every heading name the hospital's time zone, not the server's.
    return render(request, template, {**context, "time_zone": me.time_zone}, status=status)


def _form(
    request: HttpRequest,
    me: Me,
    *,
    title: str,
    specs: tuple[FieldSpec, ...],
    values: Mapping[str, str],
    cancel_url: str,
    choices: Mapping[str, tuple[Choice, ...]],
    error: DomainError | None = None,
) -> HttpResponse:
    form = build_form(
        title=title,
        action=request.path,
        submit_label="Enregistrer",
        specs=specs,
        values=values,
        error=error,
        choices=choices,
        cancel_url=cancel_url,
    )
    status = error.code.http_status if error else 200
    return _page(request, "console/form.html", me, {"form": form}, status=status)


def _confirm(request: HttpRequest, me: Me, *, label: str, cancel_url: str) -> HttpResponse:
    confirm = confirm_view(label=label, action=request.path, cancel_url=cancel_url)
    return _page(request, "console/confirm_delete.html", me, {"confirm": confirm})


def _posted(request: HttpRequest, specs: tuple[FieldSpec, ...]) -> dict[str, str]:
    return {spec.name: request.POST.get(spec.name, "") for spec in specs}


@require_GET
@require_role(Role.CLINICIAN)
def list_rules(request: HttpRequest) -> HttpResponse:
    me = _me(request)
    rules = container().availability_queries.rules_of(me.profile_id)
    department_rooms = container().reference_queries.department_rooms(me.department_id)
    rooms = {room.id: room.label for room in department_rooms}
    view = rules_view(
        rules, time_zone=me.time_zone, room_labels=rooms, done=request.GET.get("done")
    )
    return _page(request, "workspace/availability.html", me, {"view": view})


def _save_rule(
    request: HttpRequest, me: Me, *, title: str, rule: AvailabilityRule | None
) -> HttpResponse:
    specs = rule_fields(me.time_zone)
    choices = {"weekday": WEEKDAY_CHOICES, "room_id": _rooms(me)}
    if request.method == "GET":
        values = rule_values(rule) if rule else {"step_minutes": "15"}
        return _form(
            request,
            me,
            title=title,
            specs=specs,
            values=values,
            cancel_url=RULES_URL,
            choices=choices,
        )
    values = _posted(request, specs)
    try:
        container().save_availability_rule.execute(
            actor=me.user_id, rule_id=rule.id if rule else None, fields=values
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        return _form(
            request,
            me,
            title=title,
            specs=specs,
            values=values,
            cancel_url=RULES_URL,
            choices=choices,
            error=error,
        )
    return redirect(f"{RULES_URL}?done={'updated' if rule else 'created'}")


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def create_rule(request: HttpRequest) -> HttpResponse:
    return _save_rule(request, _me(request), title="Ajouter une plage", rule=None)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def edit_rule(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = _me(request)
    rule = _owned(container().availability_queries.rule(Id(record_id)), me)
    return _save_rule(request, me, title=f"Modifier la plage « {rule.label} »", rule=rule)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def delete_rule(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = _me(request)
    rule = _owned(container().availability_queries.rule(Id(record_id)), me)
    if request.method == "POST":
        container().delete_availability_rule.execute(actor=me.user_id, rule_id=rule.id)
        return redirect(f"{RULES_URL}?done=deleted")
    return _confirm(request, me, label=rule.label, cancel_url=RULES_URL)


@require_GET
@require_role(Role.CLINICIAN)
def list_time_off(request: HttpRequest) -> HttpResponse:
    me = _me(request)
    found = container().availability_queries.time_offs_of(me.profile_id)
    view = time_offs_view(found, time_zone=me.time_zone, done=request.GET.get("done"))
    return _page(request, "workspace/time_off.html", me, {"view": view})


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def create_time_off(request: HttpRequest) -> HttpResponse:
    me = _me(request)
    title = "Ajouter une absence"
    specs = time_off_fields(me.time_zone)
    if request.method == "GET":
        return _form(
            request, me, title=title, specs=specs, values={}, cancel_url=TIME_OFF_URL, choices={}
        )
    values = _posted(request, specs)
    try:
        container().record_time_off.execute(actor=me.user_id, fields=values)
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        return _form(
            request,
            me,
            title=title,
            specs=specs,
            values=values,
            cancel_url=TIME_OFF_URL,
            choices={},
            error=error,
        )
    return redirect(f"{TIME_OFF_URL}?done=created")


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
def delete_time_off(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    me = _me(request)
    found = _owned(container().availability_queries.time_off(Id(record_id)), me)
    if request.method == "POST":
        container().delete_time_off.execute(actor=me.user_id, time_off_id=found.id)
        return redirect(f"{TIME_OFF_URL}?done=deleted")
    label = time_off_label(found, me.time_zone)
    return _confirm(request, me, label=label, cancel_url=TIME_OFF_URL)
