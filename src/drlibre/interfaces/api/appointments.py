from uuid import UUID

from django.http import HttpRequest
from ninja import Query, Router, Schema, Status
from pydantic import AwareDatetime, ConfigDict, Field

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AgendaFilter,
    AppointmentStatus,
)
from drlibre.bootstrap.container import container
from drlibre.interfaces.api.booking import AppointmentOut
from drlibre.interfaces.web.auth import current_identity, identity_of
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


class AgendaQuery(Schema):
    clinician: UUID | None = None
    status: AppointmentStatus | None = None
    start: AwareDatetime | None = Field(None, alias="from")
    end: AwareDatetime | None = Field(None, alias="to")


class AgendaEntryOut(Schema):
    id: UUID
    status: str
    start: str
    end: str
    time_zone: str
    reason: str | None
    clinician: UUID
    clinician_name: str
    clinician_title: str
    specialty: str
    hospital_name: str
    hospital_address: str
    department: str
    room: str | None
    type: str
    allowed_actions: list[str]

    @staticmethod
    def of(entry: AgendaEntry) -> "AgendaEntryOut":
        appointment = entry.appointment
        return AgendaEntryOut(
            id=appointment.id.value,
            status=appointment.status.value,
            start=appointment.start.isoformat(),
            end=appointment.end.isoformat(),
            time_zone=entry.time_zone,
            reason=appointment.reason,
            clinician=appointment.clinician_id.value,
            clinician_name=entry.clinician_name,
            clinician_title=entry.clinician_title,
            specialty=entry.specialty,
            hospital_name=entry.hospital_name,
            hospital_address=entry.hospital_address,
            department=entry.department,
            room=entry.room,
            type=entry.appointment_type,
            allowed_actions=sorted(action.value for action in entry.allowed_actions),
        )


class AgendaOut(Schema):
    upcoming: list[AgendaEntryOut]
    past: list[AgendaEntryOut]


@router.get("/appointments", response=AgendaOut, auth=None)
def list_own(request: HttpRequest, query: Query[AgendaQuery]) -> AgendaOut:
    identity = current_identity(request)
    # A patient sees only their own appointments, so a `patient` parameter changes nothing.
    agenda = container().list_patient_appointments.execute(
        patient_id=identity.user_id,
        agenda_filter=AgendaFilter(
            clinician_id=Id(query.clinician) if query.clinician else None,
            status=query.status,
            start=query.start,
            end=query.end,
        ),
    )
    return AgendaOut(
        upcoming=[AgendaEntryOut.of(e) for e in agenda.upcoming],
        past=[AgendaEntryOut.of(e) for e in agenda.past],
    )


class CancelIn(Schema):
    model_config = ConfigDict(extra="forbid")

    reason: str


class RescheduleIn(Schema):
    model_config = ConfigDict(extra="forbid")

    start: AwareDatetime


@router.post("/appointments/{appointment_id}/cancel", response=AppointmentOut, auth=None)
def cancel(request: HttpRequest, appointment_id: UUID, payload: CancelIn) -> AppointmentOut:
    identity = current_identity(request)
    c = container()
    c.require_patient.execute(user_id=identity.user_id)
    cancelled = c.cancel_appointment.execute(
        appointment_id=Id(appointment_id), patient_id=identity.user_id, reason=payload.reason
    )
    return AppointmentOut.of(cancelled)


@router.post("/appointments/{appointment_id}/reschedule", response=AppointmentOut, auth=None)
def reschedule(request: HttpRequest, appointment_id: UUID, payload: RescheduleIn) -> AppointmentOut:
    identity = current_identity(request)
    c = container()
    c.require_patient.execute(user_id=identity.user_id)
    moved = c.reschedule_appointment.execute(
        appointment_id=Id(appointment_id), patient_id=identity.user_id, start=payload.start
    )
    return AppointmentOut.of(moved)
