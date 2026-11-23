from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from uuid import UUID

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from drlibre.booking.application.ports.inbound import AppointmentFile, ClinicianAction
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.forms.portal import CancelForm
from drlibre.interfaces.web.forms.workspace import NotesForm
from drlibre.interfaces.web.presenters.slots import local
from drlibre.interfaces.web.presenters.workspace import (
    NO_PROFILE,
    NOT_YOURS,
    TODAY_URL,
    appointment_page,
    appointment_url,
    calendar_page,
    cancel_page,
    day_param,
    patients_page,
    rooms_page,
    today_page,
)
from drlibre.interfaces.web.time_zones import hospital_time_zone
from drlibre.interfaces.web.views.portal import private
from drlibre.scheduling.application.ports.inbound import AvailabilityRule, FreeWeek, TimeOff
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

# Refusals the appointment pages show inline instead of an error page.
_INLINE = frozenset(
    {
        ErrorCode.INVALID_INPUT,
        ErrorCode.INVALID_TRANSITION,
        ErrorCode.RULE_VIOLATION,
        ErrorCode.CONFLICT,
        ErrorCode.NO_ROOM_AVAILABLE,
    }
)


@dataclass(frozen=True, slots=True)
class Me:
    user_id: Id
    profile_id: Id
    department_id: Id
    time_zone: str


def _me(request: HttpRequest) -> Me | None:
    user_id = current_identity(request).user_id
    profile = container().reference_queries.clinician_profile_of(user_id)
    if profile is None:
        return None
    return Me(user_id, profile.id, profile.department_id, hospital_time_zone(profile.department_id))


def current_me(request: HttpRequest) -> Me:
    me = _me(request)
    if me is None:
        raise DomainError(ErrorCode.FORBIDDEN, "Réservé aux praticiens ayant un profil.")
    return me


def owned[T: (AvailabilityRule, TimeOff)](found: T | None, me: Me) -> T:
    if found is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.")
    if found.clinician_id != me.profile_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Cet élément appartient à un autre praticien.")
    return found


def workspace_page(
    request: HttpRequest, template: str, me: Me, context: Mapping[str, object], *, status: int = 200
) -> HttpResponse:
    # The footer and every heading name the hospital's time zone, not the server's.
    return render(request, template, {**context, "time_zone": me.time_zone}, status=status)


def _private_page(
    request: HttpRequest, template: str, me: Me, view: object, *, status: int = 200
) -> HttpResponse:
    return private(workspace_page(request, template, me, {"view": view}, status=status))


type AppointmentView = Callable[[HttpRequest, Me, Id], HttpResponse]


def _own_appointment(view: AppointmentView) -> Callable[[HttpRequest, UUID], HttpResponse]:
    """Another clinician's appointment answers 403 « Not your appointment », with none of it."""

    @wraps(view)
    def wrapped(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
        me = current_me(request)
        try:
            return view(request, me, Id(appointment_id))
        except DomainError as error:
            if error.code is not ErrorCode.FORBIDDEN:
                raise
            context = {"message": NOT_YOURS, "message_lang": "en"}
            return private(render(request, "errors/403.html", context, status=403))

    return wrapped


@require_GET
@require_role(Role.CLINICIAN)
def today(request: HttpRequest) -> HttpResponse:
    me = _me(request)
    if me is None:
        # The landing page of a clinician account still waiting for its profile.
        context = {"title": "Mon espace praticien", "intro": NO_PROFILE}
        return render(request, "areas/home.html", context)
    day = container().clinician_day.execute(
        actor_id=me.user_id, day=day_param(request.GET.get("day"))
    )
    view = today_page(day, request.GET.get("done", ""))
    return _private_page(request, "workspace/today.html", me, view)


@require_GET
@require_role(Role.CLINICIAN)
def calendar(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    c = container()
    week = c.clinician_week.execute(actor_id=me.user_id, week=day_param(request.GET.get("week")))
    view = calendar_page(
        week,
        rules=c.availability_queries.rules_of(me.profile_id),
        time_offs=c.availability_queries.time_offs_of(me.profile_id),
    )
    return _private_page(request, "workspace/calendar.html", me, view)


def _file(me: Me, appointment_id: Id) -> AppointmentFile:
    return container().clinician_appointment.execute(
        actor_id=me.user_id, appointment_id=appointment_id
    )


def _week(file: AppointmentFile, raw: str | None) -> FreeWeek | None:
    """The movable appointment's week of free slots of its clinician and type."""
    a = file.entry.appointment
    if ClinicianAction.RESCHEDULE not in file.entry.actions:
        return None
    return container().find_free_week.execute(
        appointment_type_id=a.appointment_type_id,
        clinician_id=a.clinician_id,
        week=day_param(raw) or local(a.start, file.time_zone).date(),
        ignoring_appointment=a.id,
        for_patient=False,
    )


def _file_page(
    request: HttpRequest,
    me: Me,
    file: AppointmentFile,
    *,
    week: str | None = None,
    notice: str = "",
    refusal: DomainError | None = None,
    notes: NotesForm | None = None,
    status: int = 200,
) -> HttpResponse:
    view = appointment_page(
        file,
        week=_week(file, week),
        notice=notice,
        refusal=refusal,
        notes=notes,
    )
    return _private_page(request, "workspace/appointment.html", me, view, status=status)


@require_GET
@require_role(Role.CLINICIAN)
@_own_appointment
def appointment(request: HttpRequest, me: Me, appointment_id: Id) -> HttpResponse:
    file = _file(me, appointment_id)
    return _file_page(
        request, me, file, week=request.GET.get("week"), notice=request.GET.get("done", "")
    )


def _done(url: str, notice: str) -> HttpResponse:
    return redirect(f"{url}{'&' if '?' in url else '?'}done={notice}")


def _change_status(action: ClinicianAction) -> Callable[[HttpRequest, UUID], HttpResponseBase]:
    @require_POST
    @require_role(Role.CLINICIAN)
    @_own_appointment
    def view(request: HttpRequest, me: Me, appointment_id: Id) -> HttpResponse:
        c = container()
        use_case, notice = {
            ClinicianAction.CHECK_IN: (c.check_in_appointment, "checked_in"),
            ClinicianAction.COMPLETE: (c.complete_appointment, "completed"),
            ClinicianAction.NO_SHOW: (c.mark_no_show, "no_show"),
        }[action]
        try:
            changed = use_case.execute(actor_id=me.user_id, appointment_id=appointment_id)
        except DomainError as error:
            if error.code not in _INLINE:
                raise
            file = _file(me, appointment_id)
            return _file_page(request, me, file, refusal=error, status=error.code.http_status)
        if request.POST.get("from") == "day":
            day = local(changed.start, me.time_zone).date()
            return _done(f"{TODAY_URL}?day={day}", notice)
        return _done(appointment_url(appointment_id), notice)

    return view


check_in = _change_status(ClinicianAction.CHECK_IN)
complete = _change_status(ClinicianAction.COMPLETE)
no_show = _change_status(ClinicianAction.NO_SHOW)


@require_POST
@require_role(Role.CLINICIAN)
@_own_appointment
def notes(request: HttpRequest, me: Me, appointment_id: Id) -> HttpResponse:
    form = NotesForm(request.POST)
    if form.is_valid():
        try:
            container().write_clinical_notes.execute(
                actor_id=me.user_id,
                appointment_id=appointment_id,
                text=form.cleaned_data["clinical_notes"],
            )
        except DomainError as error:
            if error.code is not ErrorCode.INVALID_INPUT:
                raise
            form.refuse(error)
        else:
            return _done(appointment_url(appointment_id), "notes")
    file = _file(me, appointment_id)
    return _file_page(request, me, file, notes=form, status=ErrorCode.INVALID_INPUT.http_status)


@require_http_methods(["GET", "POST"])
@require_role(Role.CLINICIAN)
@_own_appointment
def cancel(request: HttpRequest, me: Me, appointment_id: Id) -> HttpResponse:
    file = _file(me, appointment_id)
    if request.method == "GET":
        if ClinicianAction.CANCEL not in file.entry.actions:
            return redirect(appointment_url(appointment_id))
        view = cancel_page(file, CancelForm())
        return _private_page(request, "workspace/cancel.html", me, view)
    form = CancelForm(request.POST)
    if not form.is_valid():
        view = cancel_page(file, form)
        status = ErrorCode.INVALID_INPUT.http_status
        return _private_page(request, "workspace/cancel.html", me, view, status=status)
    try:
        container().cancel_appointment.execute(
            appointment_id=appointment_id, actor_id=me.user_id, reason=form.cleaned_data["reason"]
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        view = cancel_page(file, form, error)
        return _private_page(
            request, "workspace/cancel.html", me, view, status=error.code.http_status
        )
    return _done(appointment_url(appointment_id), "cancelled")


def _start(raw: str) -> datetime:
    refused = DomainError(ErrorCode.INVALID_INPUT, "Choisissez un créneau dans la semaine.")
    try:
        start = datetime.fromisoformat(raw)
    except ValueError:
        raise refused from None
    if start.tzinfo is None:
        raise refused
    return start


@require_POST
@require_role(Role.CLINICIAN)
@_own_appointment
def reschedule(request: HttpRequest, me: Me, appointment_id: Id) -> HttpResponse:
    week = request.POST.get("week")
    try:
        container().reschedule_appointment.execute(
            appointment_id=appointment_id,
            actor_id=me.user_id,
            start=_start(request.POST.get("start", "")),
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        file = _file(me, appointment_id)
        return _file_page(
            request, me, file, week=week, refusal=error, status=error.code.http_status
        )
    return _done(appointment_url(appointment_id), "moved")


@require_GET
@require_role(Role.CLINICIAN)
def patients(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    page_request = PageRequest.from_query(page=request.GET.get("page"), search=request.GET.get("q"))
    page = container().clinician_patients.execute(actor_id=me.user_id, request=page_request)
    view = patients_page(page, search=page_request.search, time_zone=me.time_zone)
    return _private_page(request, "workspace/patients.html", me, view)


@require_GET
@require_role(Role.CLINICIAN)
def rooms(request: HttpRequest) -> HttpResponse:
    me = current_me(request)
    day = container().department_rooms_day.execute(
        actor_id=me.user_id, day=day_param(request.GET.get("day"))
    )
    return _private_page(request, "workspace/rooms.html", me, rooms_page(day))
