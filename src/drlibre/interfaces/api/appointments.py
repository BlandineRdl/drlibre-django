from uuid import UUID

from django.http import HttpRequest
from ninja import Router, Schema, Status
from pydantic import AwareDatetime, ConfigDict

from drlibre.bootstrap.container import container
from drlibre.interfaces.api.booking import AppointmentOut
from drlibre.interfaces.web.auth import identity_of
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

router = Router(tags=["appointments"])


class BookingIn(Schema):
    model_config = ConfigDict(extra="forbid")

    type: UUID
    clinician: UUID | None = None
    start: AwareDatetime


@router.post("/appointments", response={201: AppointmentOut}, auth=None)
def book(request: HttpRequest, payload: BookingIn) -> Status[AppointmentOut]:
    identity = identity_of(request)
    if identity is None:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "Connectez-vous pour continuer.")
    appointment = container().book_appointment.execute(
        patient_id=identity.user_id,
        appointment_type_id=Id(payload.type),
        clinician_id=Id(payload.clinician) if payload.clinician else None,
        start=payload.start,
    )
    return Status(201, AppointmentOut.of(appointment))
