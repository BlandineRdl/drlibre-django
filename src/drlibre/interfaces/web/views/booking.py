from datetime import datetime
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from drlibre.booking.application.ports.inbound import Appointment, HoldSummary
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity
from drlibre.interfaces.web.auth import identity_of, set_session_cookie, to_sign_in
from drlibre.interfaces.web.presenters.booking import (
    SlotContext,
    SlotRequest,
    code_page,
    confirm_choice_page,
    confirmation_page,
    details_page,
    refreshed_slots,
    refused_page,
)
from drlibre.interfaces.web.presenters.calendar_file import calendar_file
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

RESENT = "Un nouveau code vient d'être envoyé."
GONE = "Cette réservation provisoire a expiré. Choisissez un nouveau créneau."
_INLINE = frozenset(
    {
        ErrorCode.CONFLICT,
        ErrorCode.RULE_VIOLATION,
        ErrorCode.NO_CLINICIAN_AVAILABLE,
        ErrorCode.NO_ROOM_AVAILABLE,
    }
)
_NOT_FOUND = DomainError(ErrorCode.NOT_FOUND, "Créneau introuvable.")


def _uuid(raw: str | None) -> Id | None:
    try:
        return Id(UUID(raw)) if raw else None
    except ValueError:
        return None


def _parse(data: dict[str, str]) -> tuple[SlotRequest, datetime]:
    type_id = _uuid(data.get("type"))
    try:
        start = datetime.fromisoformat(data.get("start", ""))
    except ValueError:
        raise _NOT_FOUND from None
    if type_id is None or start.tzinfo is None:
        raise _NOT_FOUND
    request = SlotRequest(
        type_id=type_id,
        clinician_id=_uuid(data.get("clinician")),
        department_id=_uuid(data.get("department")),
        start=data.get("start", ""),
    )
    return request, start


def _context(type_id: Id, clinician_id: Id | None) -> SlotContext:
    c = container()
    kind = c.reference_queries.appointment_type(type_id)
    if kind is None:
        raise _NOT_FOUND
    provider = ""
    department_id = kind.department_id
    if clinician_id:
        profile = c.reference_queries.clinician_profile(clinician_id)
        member = c.staff_lookup.staff_member(profile.user_id) if profile else None
        if profile is None or member is None:
            raise _NOT_FOUND
        provider, department_id = member.full_name, profile.department_id
    department = c.reference_queries.department(department_id)
    hospital = c.reference_queries.hospital(department.hospital_id) if department else None
    if department is None or hospital is None:
        raise _NOT_FOUND
    return SlotContext(
        provider_name=provider,
        department_name=department.name,
        hospital_name=hospital.name,
        address=f"{hospital.street}, {hospital.postal_code} {hospital.city}",
        time_zone=hospital.time_zone,
        type_name=kind.name,
        duration_minutes=kind.duration_minutes,
        department_id=department_id,
    )


def _refused(
    request: HttpRequest,
    message: str,
    *,
    type_id: Id,
    clinician_id: Id | None,
    context: SlotContext,
    current_step: int,
    status: int,
) -> HttpResponse:
    found = container().next_bookable_slots.execute(
        appointment_type_id=type_id, clinician_id=clinician_id
    )
    slots = refreshed_slots(
        found,
        type_id=type_id,
        clinician_id=clinician_id,
        department_id=None if clinician_id else context.department_id,
        time_zone=context.time_zone,
    )
    view = refused_page(message, slots, time_zone=context.time_zone, current_step=current_step)
    return render(request, "booking/refused.html", {"view": view}, status=status)


def _gone(request: HttpRequest) -> HttpResponse:
    view = refused_page(GONE, (), time_zone="", current_step=1, title="Réservation expirée")
    return render(request, "booking/refused.html", {"view": view}, status=404)


@require_http_methods(["GET", "POST"])
def new(request: HttpRequest) -> HttpResponse:
    identity = identity_of(request)
    if identity is not None:
        container().require_patient.execute(user_id=identity.user_id)
    data = request.GET if request.method == "GET" else request.POST
    slot, start = _parse(data.dict())
    context = _context(slot.type_id, slot.clinician_id)
    if identity is not None:
        return _patient_flow(request, identity, slot, start, context)
    return _visitor_flow(request, slot, start, context)


def _patient_flow(
    request: HttpRequest,
    identity: Identity,
    slot: SlotRequest,
    start: datetime,
    context: SlotContext,
) -> HttpResponse:
    if request.method == "GET":
        view = confirm_choice_page(slot, context, start)
        return render(request, "booking/confirm_choice.html", {"view": view})
    try:
        appointment = container().book_appointment.execute(
            patient_id=identity.user_id,
            appointment_type_id=slot.type_id,
            clinician_id=slot.clinician_id,
            start=start,
        )
    except DomainError as error:
        if error.code not in _INLINE:
            raise
        return _refused(
            request,
            error.message,
            type_id=slot.type_id,
            clinician_id=slot.clinician_id,
            context=context,
            current_step=0,
            status=error.code.http_status,
        )
    return redirect(f"/booking/appointments/{appointment.id}")


def _visitor_flow(
    request: HttpRequest, slot: SlotRequest, start: datetime, context: SlotContext
) -> HttpResponse:
    if request.method == "GET":
        view = details_page(slot, context, start, {})
        return render(request, "booking/details.html", {"view": view})
    values = {
        key: request.POST.get(key, "")
        for key in ("full_name", "birth_date", "email", "phone", "reason", "accepted_terms")
    }
    try:
        hold = container().create_hold.execute(
            appointment_type_id=slot.type_id,
            clinician_id=slot.clinician_id,
            start=start,
            full_name=values["full_name"],
            birth_date=values["birth_date"],
            email=values["email"],
            phone=values["phone"],
            reason=values["reason"],
            accepted_terms=values["accepted_terms"] == "on",
            network=request.META.get("REMOTE_ADDR", ""),
        )
    except DomainError as error:
        if error.code is ErrorCode.INVALID_INPUT:
            view = details_page(slot, context, start, values, error)
            return render(request, "booking/details.html", {"view": view}, status=400)
        if error.code not in _INLINE:
            raise
        return _refused(
            request,
            error.message,
            type_id=slot.type_id,
            clinician_id=slot.clinician_id,
            context=context,
            current_step=1,
            status=error.code.http_status,
        )
    return redirect(f"/booking/holds/{hold.hold_id}")


@require_http_methods(["GET", "POST"])
def hold(request: HttpRequest, hold_id: UUID) -> HttpResponse:
    summary_id = Id(hold_id)
    try:
        summary = container().view_hold.execute(hold_id=summary_id)
    except DomainError:
        return _gone(request)
    context = _context(summary.appointment_type_id, summary.clinician_id)
    if not summary.open:
        return _expired(request, summary, context)
    if request.method == "GET":
        notice = RESENT if request.GET.get("resent") else ""
        view = code_page(summary, context, notice=notice)
        return render(request, "booking/code.html", {"view": view})
    try:
        verified = container().verify_hold.execute(
            hold_id=summary_id,
            code=request.POST.get("code", ""),
            user_agent=request.headers.get("User-Agent", ""),
        )
    except DomainError as error:
        if error.code is ErrorCode.INVALID_INPUT:
            view = code_page(summary, context, error=error)
            return render(request, "booking/code.html", {"view": view}, status=400)
        if error.code is ErrorCode.NOT_FOUND:
            return _expired(request, summary, context)
        raise
    if verified.appointment is not None:
        response = redirect(f"/booking/appointments/{verified.appointment.id}")
    else:
        failure = verified.failure
        response = _refused(
            request,
            failure.message if failure else GONE,
            type_id=summary.appointment_type_id,
            clinician_id=None if summary.first_available else summary.clinician_id,
            context=context,
            current_step=2,
            status=failure.code.http_status if failure else 409,
        )
    set_session_cookie(response, verified.token, verified.expires_at)
    return response


def _expired(request: HttpRequest, summary: HoldSummary, context: SlotContext) -> HttpResponse:
    return _refused(
        request,
        GONE,
        type_id=summary.appointment_type_id,
        clinician_id=None if summary.first_available else summary.clinician_id,
        context=context,
        current_step=1,
        status=404,
    )


@require_POST
def resend(request: HttpRequest, hold_id: UUID) -> HttpResponse:
    try:
        container().resend_code.execute(
            hold_id=Id(hold_id), network=request.META.get("REMOTE_ADDR", "")
        )
    except DomainError as error:
        if error.code is ErrorCode.NOT_FOUND:
            return _gone(request)
        if error.code is not ErrorCode.RULE_VIOLATION:
            raise
        summary = container().view_hold.execute(hold_id=Id(hold_id))
        context = _context(summary.appointment_type_id, summary.clinician_id)
        view = code_page(summary, context, error=error)
        return render(request, "booking/code.html", {"view": view}, status=error.code.http_status)
    return redirect(f"/booking/holds/{hold_id}?resent=1")


def _own_appointment(identity: Identity, appointment_id: UUID) -> tuple[Appointment, SlotContext]:
    found = container().view_appointment.execute(
        appointment_id=Id(appointment_id), patient_id=identity.user_id
    )
    return found, _context(found.appointment_type_id, found.clinician_id)


@require_GET
def appointment(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    identity = identity_of(request)
    if identity is None:
        return to_sign_in(request)
    found, context = _own_appointment(identity, appointment_id)
    response = render(
        request,
        "booking/confirmation.html",
        {"view": confirmation_page(found, context)},
    )
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def appointment_calendar(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    identity = identity_of(request)
    if identity is None:
        return to_sign_in(request)
    found, context = _own_appointment(identity, appointment_id)
    text = calendar_file(
        found,
        summary=f"{context.type_name} avec {context.provider_name}",
        location=f"{context.hospital_name}, {context.address}",
        stamped_at=container().clock.now(),
    )
    response = HttpResponse(text, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rendez-vous.ics"'
    response["Cache-Control"] = "no-store"
    return response
