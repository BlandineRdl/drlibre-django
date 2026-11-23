import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from drlibre.bootstrap.container import Container, container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.forms.base import WebForm
from drlibre.interfaces.web.forms.console import (
    AppointmentTypeForm,
    DepartmentForm,
    HospitalForm,
    RoomForm,
    SpecialtyForm,
)
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.reference import (
    Column,
    confirm_view,
    labels_by_id,
    list_view,
    record_values,
    yes_no,
)
from drlibre.organisation.application.ports.inbound import DeleteRecord, SaveRecord
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

INVALID = ErrorCode.INVALID_INPUT.http_status

type Choices = Mapping[str, tuple[tuple[str, str], ...]]


@dataclass(frozen=True, slots=True)
class Screen:
    slug: str
    title: str
    singular: str
    form: type[WebForm]
    columns: tuple[Column, ...]
    page: Callable[[PageRequest], Page[Any]]
    get: Callable[[Id], Any]
    save: SaveRecord
    delete: DeleteRecord
    choices: Callable[[], Choices]
    defaults: Mapping[str, str]

    @property
    def base_url(self) -> str:
        return f"/console/{self.slug}/"


def _choices(options: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((str(o.id), o.label) for o in options)


def _screens(app: Container) -> dict[str, Screen]:
    q = app.reference_queries

    @cache
    def hospital_labels() -> Mapping[Id, str]:
        return labels_by_id(q.hospital_options())

    @cache
    def department_labels() -> Mapping[Id, str]:
        return labels_by_id(q.department_options())

    def hospital_of(record: Any) -> str:
        return hospital_labels().get(record.hospital_id, "")

    def department_of(record: Any) -> str:
        return department_labels().get(record.department_id, "")

    def by_hospital() -> Choices:
        return {"hospital_id": _choices(q.hospital_options())}

    def by_department() -> Choices:
        return {"department_id": _choices(q.department_options())}

    return {
        "hospitals": Screen(
            slug="hospitals",
            title="Hôpitaux",
            singular="un hôpital",
            form=HospitalForm,
            columns=(
                Column("Nom", lambda r: r.name),
                Column("Code", lambda r: r.code),
                Column("Ville", lambda r: r.city),
                Column("Fuseau", lambda r: r.time_zone),
                Column("Actif", lambda r: yes_no(r.active)),
            ),
            page=q.hospitals,
            get=q.hospital,
            save=app.save_hospital,
            delete=app.delete_hospital,
            choices=dict,
            defaults={"time_zone": "Europe/Paris", "country": "France", "active": "on"},
        ),
        "specialties": Screen(
            slug="specialties",
            title="Spécialités",
            singular="une spécialité",
            form=SpecialtyForm,
            columns=(
                Column("Nom", lambda r: r.name),
                Column("Code", lambda r: r.code),
                Column("Active", lambda r: yes_no(r.active)),
            ),
            page=q.specialties,
            get=q.specialty,
            save=app.save_specialty,
            delete=app.delete_specialty,
            choices=dict,
            defaults={"active": "on"},
        ),
        "departments": Screen(
            slug="departments",
            title="Départements",
            singular="un département",
            form=DepartmentForm,
            columns=(
                Column("Nom", lambda r: r.name),
                Column("Code", lambda r: r.code),
                Column("Hôpital", hospital_of),
            ),
            page=q.departments,
            get=q.department,
            save=app.save_department,
            delete=app.delete_department,
            choices=by_hospital,
            defaults={},
        ),
        "rooms": Screen(
            slug="rooms",
            title="Salles",
            singular="une salle",
            form=RoomForm,
            columns=(
                Column("Nom", lambda r: r.name),
                Column("Code", lambda r: r.code),
                Column("Département", department_of),
                Column("Étage", lambda r: r.floor),
                Column("Capacité", lambda r: str(r.capacity)),
                Column("Active", lambda r: yes_no(r.active)),
            ),
            page=q.rooms,
            get=q.room,
            save=app.save_room,
            delete=app.delete_room,
            choices=by_department,
            defaults={"capacity": "1", "active": "on"},
        ),
        "appointment-types": Screen(
            slug="appointment-types",
            title="Types de RDV",
            singular="un type de RDV",
            form=AppointmentTypeForm,
            columns=(
                Column("Nom", lambda r: r.name),
                Column("Code", lambda r: r.code),
                Column("Département", department_of),
                Column("Durée", lambda r: f"{r.duration_minutes} min"),
                Column("Couleur", lambda r: r.colour),
                Column("En ligne", lambda r: yes_no(r.bookable_online)),
                Column("Actif", lambda r: yes_no(r.active)),
            ),
            page=q.appointment_types,
            get=q.appointment_type,
            save=app.save_appointment_type,
            delete=app.delete_appointment_type,
            choices=by_department,
            defaults={
                "duration_minutes": "30",
                "buffer_minutes": "0",
                "colour": "#336699",
                "active": "on",
            },
        ),
    }


def _screen(slug: str) -> Screen:
    screen = _screens(container()).get(slug)
    if screen is None:
        raise Http404
    return screen


def _record(screen: Screen, record_id: uuid.UUID) -> Any:
    record = screen.get(Id(record_id))
    if record is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.")
    return record


def _bound(screen: Screen, *args: Any, **kwargs: Any) -> WebForm:
    form = screen.form(*args, **kwargs)
    for name, choices in screen.choices().items():
        form.offer(name, choices)
    return form


def _form_page(
    request: HttpRequest, screen: Screen, form: WebForm, *, title: str, status: int = 200
) -> HttpResponse:
    page = FormPage(title, request.path, "Enregistrer", form, cancel_url=screen.base_url)
    context = {"page": page, "section_nav": console_nav(request.path)}
    return render(request, "console/form.html", context, status=status)


def _save(request: HttpRequest, screen: Screen, title: str, record_id: Id | None) -> HttpResponse:
    form = _bound(screen, request.POST)
    if not form.is_valid():
        return _form_page(request, screen, form, title=title, status=INVALID)
    try:
        screen.save.execute(
            actor=current_identity(request).user_id, record_id=record_id, fields=form.posted()
        )
    except DomainError as error:
        if error.code is not ErrorCode.INVALID_INPUT:
            raise
        form.refuse(error)
        return _form_page(request, screen, form, title=title, status=INVALID)
    return redirect(f"{screen.base_url}?done={'updated' if record_id else 'created'}")


@require_GET
@require_role(Role.ADMIN)
def list_records(request: HttpRequest, slug: str) -> HttpResponse:
    screen = _screen(slug)
    page_request = PageRequest.from_query(
        page=request.GET.get("page"), search=request.GET.get("search")
    )
    view = list_view(
        title=screen.title,
        base_url=screen.base_url,
        columns=screen.columns,
        page=screen.page(page_request),
        request=page_request,
        label=lambda record: record.label,
        done=request.GET.get("done"),
    )
    context = {
        "view": view,
        "search_label": "Rechercher par nom ou code",
        "section_nav": console_nav(request.path),
    }
    return render(request, "console/list.html", context)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def create_record(request: HttpRequest, slug: str) -> HttpResponse:
    screen = _screen(slug)
    title = f"Ajouter {screen.singular}"
    if request.method == "POST":
        return _save(request, screen, title, None)
    return _form_page(request, screen, _bound(screen, initial=screen.defaults), title=title)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def edit_record(request: HttpRequest, slug: str, record_id: uuid.UUID) -> HttpResponse:
    screen = _screen(slug)
    record = _record(screen, record_id)
    title = f"Modifier « {record.label} »"
    if request.method == "POST":
        return _save(request, screen, title, record.id)
    return _form_page(request, screen, _bound(screen, initial=record_values(record)), title=title)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def delete_record(request: HttpRequest, slug: str, record_id: uuid.UUID) -> HttpResponse:
    screen = _screen(slug)
    record = _record(screen, record_id)
    error: DomainError | None = None
    if request.method == "POST":
        try:
            screen.delete.execute(actor=current_identity(request).user_id, record_id=record.id)
        except DomainError as refused:
            if refused.code is not ErrorCode.HAS_DEPENDENTS:
                raise
            error = refused
        else:
            return redirect(f"{screen.base_url}?done=deleted")
    confirm = confirm_view(
        label=record.label, action=request.path, cancel_url=screen.base_url, error=error
    )
    context = {"confirm": confirm, "section_nav": console_nav(request.path)}
    return render(
        request,
        "console/confirm_delete.html",
        context,
        status=error.code.http_status if error else 200,
    )
