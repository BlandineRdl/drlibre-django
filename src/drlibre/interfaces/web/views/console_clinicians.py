import uuid
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.forms.console import ClinicianProfileForm
from drlibre.interfaces.web.presenters.availability import (
    AVAILABLE,
    TIME_OFF,
    week_start,
    week_view,
    weekly_summary,
)
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.reference import (
    Column,
    LinkView,
    confirm_view,
    labels_by_id,
    list_view,
    record_values,
)
from drlibre.interfaces.web.time_zones import hospital_time_zone
from drlibre.organisation.application.ports.inbound import ClinicianProfile
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

BASE = "/console/clinicians/"
INVALID = ErrorCode.INVALID_INPUT.http_status


def _profile(record_id: uuid.UUID) -> ClinicianProfile:
    profile = container().reference_queries.clinician_profile(Id(record_id))
    if profile is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Profil introuvable.")
    return profile


def _names() -> Mapping[Id, str]:
    return {m.user_id: m.full_name for m in container().staff_lookup.active_clinicians()}


def _options(options: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((str(o.id), o.label) for o in options)


def _profile_form(*args: Any, attaching: bool, **kwargs: Any) -> ClinicianProfileForm:
    q = container().reference_queries
    form = ClinicianProfileForm(*args, attaching=attaching, **kwargs)
    form.offer("department_id", _options(q.department_options()))
    form.offer("specialty_id", _options(q.specialty_options()))
    form.offer("default_room_id", _options(q.room_options()))
    if attaching:
        taken = q.profiled_user_ids()
        free = [m for m in container().staff_lookup.active_clinicians() if m.user_id not in taken]
        form.offer("user_id", ((str(m.user_id), m.full_name) for m in free))
    return form


def _form(
    request: HttpRequest, form: ClinicianProfileForm, *, title: str, status: int = 200
) -> HttpResponse:
    page = FormPage(title, request.path, "Enregistrer", form, cancel_url=BASE)
    context = {"page": page, "section_nav": console_nav(request.path)}
    return render(request, "console/form.html", context, status=status)


@require_GET
@require_role(Role.ADMIN)
def list_clinicians(request: HttpRequest) -> HttpResponse:
    q = container().reference_queries
    names = _names()
    departments = labels_by_id(q.department_options())
    specialties = labels_by_id(q.specialty_options())
    page_request = PageRequest.from_query(
        page=request.GET.get("page"), search=request.GET.get("search")
    )
    search = page_request.search
    named = container().staff_lookup.named_like(search) if search else frozenset()
    page = q.clinician_profiles(page_request, named=named)
    rules = container().availability_queries.weekly_summary(frozenset(p.id for p in page.items))

    def named(p: ClinicianProfile) -> str:
        # The title is an honorific shared by many; the name tells the rows apart.
        return names.get(p.user_id, p.title)

    columns = (
        Column("Praticien", lambda p: names.get(p.user_id, "Compte inactif")),
        Column("Titre", lambda p: p.title),
        Column("Département", lambda p: departments.get(p.department_id, "")),
        Column("Spécialité", lambda p: specialties.get(p.specialty_id, "")),
        Column("Poids", lambda p: str(p.weight)),
        Column("Plages (heure locale de l'hôpital)", lambda p: weekly_summary(rules.get(p.id, ()))),
    )
    view = list_view(
        title="Praticiens",
        base_url=BASE,
        columns=columns,
        page=page,
        request=page_request,
        label=named,
        done=request.GET.get("done"),
        links=lambda p: (LinkView(f"{BASE}{p.id}/week", "Semaine", f"Calendrier de {named(p)}"),),
    )
    context = {
        "view": view,
        "search_label": "Rechercher par nom ou titre",
        "section_nav": console_nav(request.path),
    }
    return render(request, "console/list.html", context)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def attach_profile(request: HttpRequest) -> HttpResponse:
    title = "Rattacher un profil praticien"
    if request.method == "GET":
        return _form(request, _profile_form(initial={"weight": 1}, attaching=True), title=title)
    form = _profile_form(request.POST, attaching=True)
    if not form.is_valid():
        return _form(request, form, title=title, status=INVALID)
    fields = form.posted()
    try:
        container().attach_clinician_profile.execute(
            actor=current_identity(request).user_id, user_id=fields["user_id"], fields=fields
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        form.refuse(error)
        return _form(request, form, title=title, status=INVALID)
    return redirect(f"{BASE}?done=created")


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def edit_profile(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    profile = _profile(record_id)
    title = f"Profil praticien de « {_names().get(profile.user_id, profile.title)} »"
    if request.method == "GET":
        form = _profile_form(initial=record_values(profile), attaching=False)
        return _form(request, form, title=title)
    form = _profile_form(request.POST, attaching=False)
    if not form.is_valid():
        return _form(request, form, title=title, status=INVALID)
    try:
        container().edit_clinician_profile.execute(
            actor=current_identity(request).user_id, profile_id=profile.id, fields=form.posted()
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        form.refuse(error)
        return _form(request, form, title=title, status=INVALID)
    return redirect(f"{BASE}?done=updated")


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def delete_profile(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    profile = _profile(record_id)
    error: DomainError | None = None
    if request.method == "POST":
        try:
            container().delete_clinician_profile.execute(
                actor=current_identity(request).user_id, profile_id=profile.id
            )
        except DomainError as refused:
            if refused.code is not ErrorCode.HAS_DEPENDENTS:
                raise
            error = refused
        else:
            return redirect(f"{BASE}?done=deleted")
    confirm = confirm_view(
        label=_names().get(profile.user_id, profile.title),
        action=request.path,
        cancel_url=BASE,
        error=error,
    )
    context = {"confirm": confirm, "section_nav": console_nav(request.path)}
    status = error.code.http_status if error else 200
    return render(request, "console/confirm_delete.html", context, status=status)


@require_GET
@require_role(Role.ADMIN)
def clinician_week(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    profile = _profile(record_id)
    time_zone = hospital_time_zone(profile.department_id)
    today = container().clock.now().astimezone(ZoneInfo(time_zone)).date()
    q = container().availability_queries
    week = week_view(
        clinician=_names().get(profile.user_id, profile.title),
        time_zone=time_zone,
        monday=week_start(request.GET.get("week"), today=today),
        rules=q.rules_of(profile.id),
        time_offs=q.time_offs_of(profile.id),
        base_url=request.path,
    )
    context = {
        "week": week,
        "available": AVAILABLE,
        "time_off": TIME_OFF,
        "time_zone": time_zone,
        "section_nav": console_nav(request.path),
    }
    return render(request, "console/clinician_week.html", context)
