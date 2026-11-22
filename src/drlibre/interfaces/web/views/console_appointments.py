import csv
import uuid
from collections.abc import Callable
from datetime import datetime

from django.http import HttpRequest, HttpResponse, HttpResponseBase, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from drlibre.booking.application.ports.inbound import (
    AppointmentFile,
    ClinicianAction,
)
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.console_appointments import (
    CONSOLE_APPOINTMENTS_URL,
    BookChoice,
    appointment_filter,
    appointment_url,
    book_page,
    cancel_page,
    csv_rows,
    file_page,
    list_page,
)
from drlibre.interfaces.web.presenters.slots import local
from drlibre.interfaces.web.presenters.workspace import day_param
from drlibre.interfaces.web.views.portal import private
from drlibre.scheduling.application.ports.inbound import FreeWeek
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from drlibre.shared_kernel.validation import invalid_field, parse_id

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


def _render(
    request: HttpRequest, template: str, context: dict[str, object], *, status: int = 200
) -> HttpResponse:
    context = {**context, "section_nav": console_nav(CONSOLE_APPOINTMENTS_URL)}
    return private(render(request, template, context, status=status))


def _actor(request: HttpRequest) -> Id:
    return current_identity(request).user_id


@require_GET
@require_role(Role.ADMIN)
def list_appointments(request: HttpRequest) -> HttpResponse:
    shown = appointment_filter(request.GET)
    c = container()
    page = c.list_all_appointments.execute(
        actor_id=_actor(request),
        appointment_filter=shown,
        request=PageRequest.from_query(page=request.GET.get("page"), search=None),
    )
    view = list_page(
        page,
        shown,
        departments=c.reference_queries.department_options(),
        clinicians=c.booking_option_queries.clinician_options(),
    )
    return _render(request, "console/appointments.html", {"view": view})


class _Echo:
    """A file-like sink: csv.writer hands back each line instead of buffering it."""

    def write(self, value: str) -> str:
        return value


@require_GET
@require_role(Role.ADMIN)
def export(request: HttpRequest) -> StreamingHttpResponse:
    rows = container().export_appointments.execute(
        actor_id=_actor(request), appointment_filter=appointment_filter(request.GET)
    )
    writer = csv.writer(_Echo())
    response = StreamingHttpResponse(
        (writer.writerow(line) for line in csv_rows(rows)), content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="rendez-vous.csv"'
    response["Cache-Control"] = "no-store"
    return response


def _file(request: HttpRequest, appointment_id: Id) -> AppointmentFile:
    return container().clinician_appointment.execute(
        actor_id=_actor(request), appointment_id=appointment_id
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
    file: AppointmentFile,
    *,
    week: str | None = None,
    notice: str = "",
    refusal: DomainError | None = None,
) -> HttpResponse:
    view = file_page(file, week=_week(file, week), notice=notice, refusal=refusal)
    status = refusal.code.http_status if refusal else 200
    return _render(request, "console/appointment.html", {"view": view}, status=status)


def _done(appointment_id: Id, notice: str) -> HttpResponse:
    return redirect(f"{appointment_url(appointment_id)}?done={notice}")


@require_GET
@require_role(Role.ADMIN)
def appointment(request: HttpRequest, appointment_id: uuid.UUID) -> HttpResponse:
    file = _file(request, Id(appointment_id))
    return _file_page(
        request, file, week=request.GET.get("week"), notice=request.GET.get("done", "")
    )


def _change_status(
    action: ClinicianAction,
) -> Callable[[HttpRequest, uuid.UUID], HttpResponseBase]:
    @require_POST
    @require_role(Role.ADMIN)
    def view(request: HttpRequest, appointment_id: uuid.UUID) -> HttpResponse:
        c = container()
        use_case, notice = {
            ClinicianAction.CHECK_IN: (c.check_in_appointment, "checked_in"),
            ClinicianAction.COMPLETE: (c.complete_appointment, "completed"),
            ClinicianAction.NO_SHOW: (c.mark_no_show, "no_show"),
        }[action]
        target = Id(appointment_id)
        try:
            use_case.execute(actor_id=_actor(request), appointment_id=target)
        except DomainError as error:
            if error.code not in _INLINE:
                raise
            return _file_page(request, _file(request, target), refusal=error)
        return _done(target, notice)

    return view


check_in = _change_status(ClinicianAction.CHECK_IN)
complete = _change_status(ClinicianAction.COMPLETE)
no_show = _change_status(ClinicianAction.NO_SHOW)


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def cancel(request: HttpRequest, appointment_id: uuid.UUID) -> HttpResponse:
    target = Id(appointment_id)
    file = _file(request, target)
    if request.method == "GET":
        if ClinicianAction.CANCEL not in file.entry.actions:
            return redirect(appointment_url(target))
        return _render(request, "console/appointment_cancel.html", {"view": cancel_page(file, {})})
    values = {"reason": request.POST.get("reason", "")}
    try:
        container().cancel_appointment.execute(
            appointment_id=target, actor_id=_actor(request), reason=values["reason"]
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        view = cancel_page(file, values, error)
        return _render(
            request,
            "console/appointment_cancel.html",
            {"view": view},
            status=error.code.http_status,
        )
    return _done(target, "cancelled")


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
@require_role(Role.ADMIN)
def reschedule(request: HttpRequest, appointment_id: uuid.UUID) -> HttpResponse:
    target = Id(appointment_id)
    try:
        container().reschedule_appointment.execute(
            appointment_id=target,
            actor_id=_actor(request),
            start=_start(request.POST.get("start", "")),
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        file = _file(request, target)
        return _file_page(request, file, week=request.POST.get("week"), refusal=error)
    return _done(target, "moved")


def _book_view(
    request: HttpRequest, choice: BookChoice, *, week: str | None, error: DomainError | None
) -> HttpResponse:
    c = container()
    kind_id = parse_id(choice.appointment_type)
    options = c.booking_option_queries.booking_options(kind_id) if kind_id else None
    clinicians = options.clinicians if options else ()
    clinician = next((o.id for o in clinicians if str(o.id) == choice.clinician), None)
    free, upcoming = None, ()
    if kind_id is not None and clinician is not None and parse_id(choice.patient):
        free = c.find_free_week.execute(
            appointment_type_id=kind_id,
            clinician_id=clinician,
            week=day_param(week),
            for_patient=False,
        )
        if not free.slots:
            upcoming = tuple(
                s.start
                for s in c.next_bookable_slots.execute(
                    appointment_type_id=kind_id, clinician_id=clinician
                )
            )
    view = book_page(
        choice,
        patients=c.patient_lookup.active_patients(choice.search) if choice.search else (),
        types=c.booking_option_queries.type_options(online_only=False),
        clinicians=clinicians,
        rooms=options.rooms if options else (),
        week=free,
        error=error,
        upcoming=upcoming,
    )
    status = error.code.http_status if error else 200
    return _render(request, "console/book.html", {"view": view}, status=status)


def _choice(data: dict[str, str]) -> BookChoice:
    return BookChoice(
        search=data.get("q", "").strip()[:100],
        patient=data.get("patient", ""),
        appointment_type=data.get("type", ""),
        clinician=data.get("clinician", ""),
        room=data.get("room", ""),
    )


@require_http_methods(["GET", "POST"])
@require_role(Role.ADMIN)
def book(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return _book_view(
            request, _choice(request.GET.dict()), week=request.GET.get("week"), error=None
        )
    data = request.POST.dict()
    choice = _choice(data)
    try:
        kind_id = parse_id(choice.appointment_type)
        if kind_id is None:
            raise invalid_field("type", "Choisissez un type de RDV.")
        booked = container().book_appointment_as_caller.execute(
            actor_id=_actor(request),
            appointment_type_id=kind_id,
            start=_start(data.get("start", "")),
            clinician_id=parse_id(choice.clinician),
            patient_id=parse_id(choice.patient),
            room_id=parse_id(choice.room) if choice.room else None,
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        return _book_view(request, choice, week=data.get("week"), error=error)
    return _done(booked.id, "booked")
