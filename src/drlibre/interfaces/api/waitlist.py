from datetime import date
from uuid import UUID

from django.http import HttpRequest
from ninja import Router, Schema, Status
from pydantic import ConfigDict

from drlibre.booking.application.ports.inbound import WaitlistEntry
from drlibre.bootstrap.container import container
from drlibre.interfaces.api.booking import AppointmentOut
from drlibre.interfaces.web.auth import current_identity
from drlibre.shared_kernel.ids import Id

router = Router(tags=["waitlist"])


class JoinIn(Schema):
    model_config = ConfigDict(extra="forbid")

    appointment_type_id: UUID
    clinician_id: UUID | None = None
    from_date: date
    to_date: date
    patient_email: str | None = None


class WaitlistEntryOut(Schema):
    id: UUID
    patient: UUID
    type: UUID
    clinician: UUID | None
    earliest: str
    latest: str
    status: str
    created_at: str
    offered_appointment: UUID | None

    @staticmethod
    def of(entry: WaitlistEntry) -> "WaitlistEntryOut":
        offered = entry.offered_appointment_id
        return WaitlistEntryOut(
            id=entry.id.value,
            patient=entry.patient_id.value,
            type=entry.appointment_type_id.value,
            clinician=entry.clinician_id.value if entry.clinician_id else None,
            earliest=entry.earliest.isoformat(),
            latest=entry.latest.isoformat(),
            status=entry.status.value,
            created_at=entry.created_at.isoformat(),
            offered_appointment=offered.value if offered else None,
        )


@router.post("/waitlist", response={201: WaitlistEntryOut}, auth=None)
def join(request: HttpRequest, payload: JoinIn) -> Status[WaitlistEntryOut]:
    entry = container().join_waitlist.execute(
        actor_id=current_identity(request).user_id,
        appointment_type_id=Id(payload.appointment_type_id),
        clinician_id=Id(payload.clinician_id) if payload.clinician_id else None,
        from_date=payload.from_date,
        to_date=payload.to_date,
        patient_email=payload.patient_email,
    )
    return Status(201, WaitlistEntryOut.of(entry))


@router.post("/waitlist/{entry_id}/accept", response={201: AppointmentOut}, auth=None)
def accept(request: HttpRequest, entry_id: UUID) -> Status[AppointmentOut]:
    appointment = container().accept_waitlist_offer.execute(
        actor_id=current_identity(request).user_id, entry_id=Id(entry_id)
    )
    return Status(201, AppointmentOut.of(appointment))
