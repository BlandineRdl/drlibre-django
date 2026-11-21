from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema, Status
from pydantic import AwareDatetime, ConfigDict

from drlibre.booking.application.ports.inbound import Appointment
from drlibre.bootstrap.container import container
from drlibre.interfaces.web.auth import set_session_cookie
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id

router = Router(tags=["booking"])


class HoldIn(Schema):
    model_config = ConfigDict(extra="forbid")

    type: UUID
    clinician: UUID | None = None
    start: AwareDatetime
    full_name: str
    birth_date: str
    email: str
    phone: str = ""
    reason: str = ""
    accepted_terms: bool


class HoldOut(Schema):
    hold_id: UUID
    provider_id: UUID
    expires_at: str


class VerifyIn(Schema):
    model_config = ConfigDict(extra="forbid")

    code: str


class AppointmentOut(Schema):
    id: UUID
    clinician: UUID
    type: UUID
    start: str
    end: str
    status: str

    @staticmethod
    def of(appointment: Appointment) -> "AppointmentOut":
        return AppointmentOut(
            id=appointment.id.value,
            clinician=appointment.clinician_id.value,
            type=appointment.appointment_type_id.value,
            start=appointment.start.isoformat(),
            end=appointment.end.isoformat(),
            status=appointment.status.value,
        )


class FailureOut(Schema):
    code: str
    message: str
    details: dict[str, object]


class VerifiedOut(Schema):
    appointment: AppointmentOut | None
    failure: FailureOut | None


@router.post("/booking/holds", response={201: HoldOut}, auth=None)
def create_hold(request: HttpRequest, payload: HoldIn) -> Status[HoldOut]:
    hold = container().create_hold.execute(
        appointment_type_id=Id(payload.type),
        clinician_id=Id(payload.clinician) if payload.clinician else None,
        start=payload.start,
        full_name=payload.full_name,
        birth_date=payload.birth_date,
        email=payload.email,
        phone=payload.phone,
        reason=payload.reason,
        accepted_terms=payload.accepted_terms,
        network=request.META.get("REMOTE_ADDR", ""),
    )
    out = HoldOut(
        hold_id=hold.hold_id.value,
        provider_id=hold.clinician_id.value,
        expires_at=hold.expires_at.isoformat(),
    )
    return Status(201, out)


@router.post("/booking/holds/{hold_id}/verify", response=VerifiedOut, auth=None)
def verify_hold(
    request: HttpRequest, hold_id: UUID, payload: VerifyIn, response: HttpResponse
) -> VerifiedOut:
    verified = container().verify_hold.execute(
        hold_id=Id(hold_id),
        code=payload.code,
        user_agent=request.headers.get("User-Agent", ""),
    )
    set_session_cookie(response, verified.token, verified.expires_at)
    outcome = verified.outcome
    if isinstance(outcome, DomainError):
        failure = FailureOut(
            code=outcome.code.value, message=outcome.message, details=outcome.details
        )
        return VerifiedOut(appointment=None, failure=failure)
    return VerifiedOut(appointment=AppointmentOut.of(outcome), failure=None)


@router.post("/booking/holds/{hold_id}/resend", response={204: None}, auth=None)
def resend_code(request: HttpRequest, hold_id: UUID) -> Status[None]:
    container().resend_code.execute(
        hold_id=Id(hold_id), network=request.META.get("REMOTE_ADDR", "")
    )
    return Status(204, None)
