from datetime import date, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AgendaFilter,
    PatientAppointments,
)
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity, Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.forms.base import INVALID, iso, options
from drlibre.interfaces.web.forms.portal import CancelForm, ProfileForm, WaitlistJoinForm
from drlibre.interfaces.web.presenters.calendar_file import calendar_file
from drlibre.interfaces.web.presenters.portal import (
    APPOINTMENTS_URL,
    NOTIFICATIONS_URL,
    PROFILE_URL,
    appointment_day,
    appointments_page,
    cancel_page,
    home_page,
    notifications_page,
    profile_page,
    profile_values,
    reschedule_page,
)
from drlibre.interfaces.web.presenters.waitlist import WAITLIST_URL, refusal_text, waitlist_page
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest

# Refusals the cancel and reschedule pages show inline instead of an error page.
_INLINE = frozenset(
    {
        ErrorCode.INVALID_INPUT,
        ErrorCode.RULE_VIOLATION,
        ErrorCode.INVALID_TRANSITION,
        ErrorCode.CONFLICT,
        ErrorCode.NO_ROOM_AVAILABLE,
    }
)
_ONE_INSTANT = timedelta(microseconds=1)


def _agenda(identity: Identity, agenda_filter: AgendaFilter | None = None) -> PatientAppointments:
    return container().list_patient_appointments.execute(
        patient_id=identity.user_id, agenda_filter=agenda_filter or AgendaFilter()
    )


def _entry(identity: Identity, appointment_id: UUID) -> AgendaEntry:
    """The patient's own appointment as listed; forbidden or not_found through the use case."""
    found = container().view_appointment.execute(
        appointment_id=Id(appointment_id), patient_id=identity.user_id
    )
    agenda = _agenda(identity, AgendaFilter(start=found.start, end=found.start + _ONE_INSTANT))
    listed = next((e for e in agenda.upcoming + agenda.past if e.appointment.id == found.id), None)
    if listed is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
    return listed


def private(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store"
    return response


@require_GET
@require_role(Role.PATIENT)
def home(request: HttpRequest) -> HttpResponse:
    identity = current_identity(request)
    unread = container().count_unread.execute(recipient_id=identity.user_id)
    view = home_page(identity.full_name, _agenda(identity), unread)
    return private(render(request, "portal/home.html", {"view": view}))


@require_GET
@require_role(Role.PATIENT)
def appointments(request: HttpRequest) -> HttpResponse:
    view = appointments_page(_agenda(current_identity(request)), request.GET.get("done", ""))
    return private(render(request, "portal/appointments.html", {"view": view}))


@require_http_methods(["GET", "POST"])
@require_role(Role.PATIENT)
def cancel(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    identity = current_identity(request)
    entry = _entry(identity, appointment_id)
    if request.method == "GET":
        return render(request, "portal/cancel.html", {"view": cancel_page(entry, CancelForm())})
    form = CancelForm(request.POST)
    if not form.is_valid():
        view = cancel_page(entry, form)
        return render(request, "portal/cancel.html", {"view": view}, status=INVALID)
    try:
        container().cancel_appointment.execute(
            appointment_id=entry.appointment.id,
            actor_id=identity.user_id,
            reason=form.cleaned_data["reason"],
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        view = cancel_page(entry, form, error)
        return render(request, "portal/cancel.html", {"view": view}, status=error.code.http_status)
    return redirect(f"{APPOINTMENTS_URL}?done=cancelled")


def _week(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _start(raw: str) -> datetime:
    refused = DomainError(ErrorCode.INVALID_INPUT, "Choisissez un créneau dans la semaine.")
    try:
        start = datetime.fromisoformat(raw)
    except ValueError:
        raise refused from None
    if start.tzinfo is None:
        raise refused
    return start


@require_http_methods(["GET", "POST"])
@require_role(Role.PATIENT)
def reschedule(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    identity = current_identity(request)
    entry = _entry(identity, appointment_id)
    data = request.GET if request.method == "GET" else request.POST
    week = container().find_free_week.execute(
        appointment_type_id=entry.appointment.appointment_type_id,
        clinician_id=entry.appointment.clinician_id,
        week=_week(data.get("week")) or appointment_day(entry),
        ignoring_appointment=entry.appointment.id,
    )
    if request.method == "GET":
        return render(request, "portal/reschedule.html", {"view": reschedule_page(entry, week)})
    try:
        container().reschedule_appointment.execute(
            appointment_id=entry.appointment.id,
            actor_id=identity.user_id,
            start=_start(request.POST.get("start", "")),
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        view = reschedule_page(entry, week, error)
        return render(
            request, "portal/reschedule.html", {"view": view}, status=error.code.http_status
        )
    return redirect(f"{APPOINTMENTS_URL}?done=moved")


@require_GET
@require_role(Role.PATIENT)
def appointment_calendar(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    entry = _entry(current_identity(request), appointment_id)
    text = calendar_file(
        entry.appointment,
        summary=f"{entry.appointment_type} avec {entry.clinician_name}",
        location=f"{entry.hospital_name}, {entry.hospital_address}",
        stamped_at=container().clock.now(),
    )
    response = HttpResponse(text, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rendez-vous.ics"'
    return private(response)


@require_GET
@require_role(Role.PATIENT)
def notifications(request: HttpRequest) -> HttpResponse:
    page = container().list_notifications.execute(
        recipient_id=current_identity(request).user_id,
        request=PageRequest.from_query(page=request.GET.get("page"), search=None),
    )
    view = notifications_page(page, settings.TIME_ZONE)
    return private(render(request, "portal/notifications.html", {"view": view}))


@require_POST
@require_role(Role.PATIENT)
def mark_read(request: HttpRequest, notification_id: UUID) -> HttpResponse:
    container().mark_notification_read.execute(
        user_id=current_identity(request).user_id, notification_id=Id(notification_id)
    )
    return redirect(NOTIFICATIONS_URL)


@require_http_methods(["GET", "POST"])
@require_role(Role.PATIENT)
def profile(request: HttpRequest) -> HttpResponse:
    identity = current_identity(request)
    c = container()
    user = c.user_queries.user(identity.user_id)
    if user is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Profil introuvable.")
    if request.method == "GET":
        view = profile_page(
            user,
            ProfileForm(initial=profile_values(user)),
            has_password=identity.has_password,
            notice=request.GET.get("done", ""),
        )
        return private(render(request, "portal/profile.html", {"view": view}))
    form = ProfileForm(request.POST)
    if form.is_valid():
        try:
            c.update_profile.execute(
                actor_id=identity.user_id,
                user_id=identity.user_id,
                phone=form.cleaned_data["phone"],
                birth_date=iso(form.cleaned_data["birth_date"]),
            )
        except DomainError as error:
            if error.code is not ErrorCode.INVALID_INPUT:
                raise
            form.refuse(error)
        else:
            return redirect(f"{PROFILE_URL}?done=saved")
    view = profile_page(user, form, has_password=identity.has_password)
    return render(request, "portal/profile.html", {"view": view}, status=INVALID)


def _join_form(request: HttpRequest | None = None) -> WaitlistJoinForm:
    c = container()
    return WaitlistJoinForm(
        request.POST if request else None,
        types=options(c.booking_option_queries.type_options(online_only=True)),
        clinicians=options(c.booking_option_queries.clinician_options()),
    )


def _waitlist_page(
    request: HttpRequest,
    form: WaitlistJoinForm,
    *,
    status: int = 200,
    error: DomainError | None = None,
) -> HttpResponse:
    c = container()
    view = waitlist_page(
        c.waitlist_queries.own_entries(current_identity(request).user_id),
        form,
        c.clock.now(),
        notice=request.GET.get("done", ""),
        error=error,
    )
    return private(render(request, "portal/waitlist.html", {"view": view}, status=status))


@require_http_methods(["GET", "POST"])
@require_role(Role.PATIENT)
def waitlist(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return _waitlist_page(request, _join_form())
    form = _join_form(request)
    if not form.is_valid():
        return _waitlist_page(request, form, status=INVALID)
    try:
        container().join_waitlist.execute(
            actor_id=current_identity(request).user_id, patient_email=None, **form.cleaned_data
        )
    except DomainError as error:
        if error.code not in _INLINE | {ErrorCode.NOT_FOUND}:
            raise
        form.refuse(error, refusal_text(error))
        return _waitlist_page(request, form, status=error.code.http_status)
    return redirect(f"{WAITLIST_URL}?done=joined")


@require_POST
@require_role(Role.PATIENT)
def accept_offer(request: HttpRequest, entry_id: UUID) -> HttpResponse:
    try:
        container().accept_waitlist_offer.execute(
            actor_id=current_identity(request).user_id, entry_id=Id(entry_id)
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        return _waitlist_page(request, _join_form(), status=error.code.http_status, error=error)
    return redirect(f"{APPOINTMENTS_URL}?done=booked")
