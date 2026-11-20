import uuid
from collections.abc import Mapping

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.forms import Choice, build_form
from drlibre.interfaces.web.presenters.reference import (
    Column,
    labels_by_id,
    list_view,
    record_values,
)
from drlibre.interfaces.web.presenters.staff import CLINICIAN_FIELD, PROFILE_FIELDS
from drlibre.organisation.application.ports.inbound import ClinicianProfile
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

BASE = "/console/clinicians/"


def _profile(record_id: uuid.UUID) -> ClinicianProfile:
    profile = container().reference_queries.clinician_profile(Id(record_id))
    if profile is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Profil introuvable.")
    return profile


def _names() -> Mapping[Id, str]:
    return {m.user_id: m.full_name for m in container().staff_lookup.active_clinicians()}


def _choices(*, attaching: bool) -> dict[str, tuple[Choice, ...]]:
    q = container().reference_queries
    choices = {
        "department_id": tuple(Choice(str(o.id), o.label) for o in q.department_options()),
        "specialty_id": tuple(Choice(str(o.id), o.label) for o in q.specialty_options()),
        "default_room_id": tuple(Choice(str(o.id), o.label) for o in q.room_options()),
    }
    if attaching:
        taken = q.profiled_user_ids()
        free = [m for m in container().staff_lookup.active_clinicians() if m.user_id not in taken]
        choices["user_id"] = tuple(Choice(str(m.user_id), m.full_name) for m in free)
    return choices


def _form(
    request: HttpRequest,
    *,
    title: str,
    values: Mapping[str, str],
    attaching: bool,
    error: DomainError | None = None,
) -> HttpResponse:
    specs = (CLINICIAN_FIELD, *PROFILE_FIELDS) if attaching else PROFILE_FIELDS
    form = build_form(
        title=title,
        action=request.path,
        submit_label="Enregistrer",
        specs=specs,
        values=values,
        error=error,
        choices=_choices(attaching=attaching),
        cancel_url=BASE,
    )
    context = {"form": form, "section_nav": console_nav(request.path)}
    return render(
        request, "console/form.html", context, status=error.code.http_status if error else 200
    )


def _posted(request: HttpRequest) -> dict[str, str]:
    return {
        spec.name: request.POST.get(spec.name, "") for spec in (CLINICIAN_FIELD, *PROFILE_FIELDS)
    }


@require_GET
@require_role(Role.ADMIN)
def list_clinicians(request: HttpRequest) -> HttpResponse:
    q = container().reference_queries
    names = _names()
    departments = labels_by_id(q.department_options())
    specialties = labels_by_id(q.specialty_options())
    columns = (
        Column("Praticien", lambda p: names.get(p.user_id, "Compte inactif")),
        Column("Titre", lambda p: p.title),
        Column("Département", lambda p: departments.get(p.department_id, "")),
        Column("Spécialité", lambda p: specialties.get(p.specialty_id, "")),
        Column("Poids", lambda p: str(p.weight)),
    )
    page_request = PageRequest.from_query(
        page=request.GET.get("page"), search=request.GET.get("search")
    )
    view = list_view(
        title="Praticiens",
        base_url=BASE,
        columns=columns,
        page=q.clinician_profiles(page_request),
        request=page_request,
        label=lambda p: p.title,
        done=request.GET.get("done"),
        deletable=False,
    )
    context = {
        "view": view,
        "search_label": "Rechercher par titre",
        "section_nav": console_nav(request.path),
    }
    return render(request, "console/list.html", context)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def attach_profile(request: HttpRequest) -> HttpResponse:
    title = "Rattacher un profil praticien"
    if request.method == "GET":
        return _form(request, title=title, values={"weight": "1"}, attaching=True)
    values = _posted(request)
    try:
        container().attach_clinician_profile.execute(
            actor=current_identity(request).user_id, user_id=values["user_id"], fields=values
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        return _form(request, title=title, values=values, attaching=True, error=error)
    return redirect(f"{BASE}?done=created")


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def edit_profile(request: HttpRequest, record_id: uuid.UUID) -> HttpResponse:
    profile = _profile(record_id)
    title = f"Profil praticien de « {_names().get(profile.user_id, profile.title)} »"
    if request.method == "GET":
        return _form(request, title=title, values=record_values(profile), attaching=False)
    values = _posted(request)
    try:
        container().edit_clinician_profile.execute(
            actor=current_identity(request).user_id, profile_id=profile.id, fields=values
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        return _form(request, title=title, values=values, attaching=False, error=error)
    return redirect(f"{BASE}?done=updated")
