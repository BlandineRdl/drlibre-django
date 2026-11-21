from uuid import UUID

from django.http import HttpRequest
from ninja import Query, Router, Schema, Status
from pydantic import AwareDatetime, ConfigDict, Field

from drlibre.booking.application.ports.inbound import (
    AdminAppointmentRow,
    AgendaEntry,
    AppointmentsQuery,
    AppointmentStatus,
    ClinicianAppointments,
    ClinicianEntry,
    Source,
)
from drlibre.bootstrap.container import container
from drlibre.interfaces.api.booking import AppointmentOut
from drlibre.interfaces.web.auth import current_identity
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

router = Router(tags=["appointments"])


class BookingIn(Schema):
    model_config = ConfigDict(extra="forbid")

    type: UUID
    clinician: UUID | None = None
    start: AwareDatetime
    patient: UUID | None = None
    room: UUID | None = None


def _optional_id(raw: UUID | None) -> Id | None:
    return Id(raw) if raw else None


@router.post("/appointments", response={201: AppointmentOut}, auth=None)
def book(request: HttpRequest, payload: BookingIn) -> Status[AppointmentOut]:
    identity = current_identity(request)
    appointment = container().book_appointment_as_caller.execute(
        actor_id=identity.user_id,
        appointment_type_id=Id(payload.type),
        start=payload.start,
        clinician_id=_optional_id(payload.clinician),
        patient_id=_optional_id(payload.patient),
        room_id=_optional_id(payload.room),
    )
    return Status(201, AppointmentOut.of(appointment))


class AgendaQuery(Schema):
    clinician: UUID | None = None
    patient: UUID | None = None
    status: AppointmentStatus | None = None
    start: AwareDatetime | None = Field(None, alias="from")
    end: AwareDatetime | None = Field(None, alias="to")
    department: UUID | None = None
    source: Source | None = None
    page: int = Field(1, ge=1)


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


class ClinicianEntryOut(Schema):
    id: UUID
    status: str
    start: str
    end: str
    reason: str | None
    patient: UUID
    patient_name: str
    type: str
    room: str | None
    allowed_actions: list[str]

    @staticmethod
    def of(entry: ClinicianEntry) -> "ClinicianEntryOut":
        appointment = entry.appointment
        return ClinicianEntryOut(
            id=appointment.id.value,
            status=appointment.status.value,
            start=appointment.start.isoformat(),
            end=appointment.end.isoformat(),
            reason=appointment.reason,
            patient=appointment.patient_id.value,
            patient_name=entry.patient_name,
            type=entry.appointment_type,
            room=entry.room,
            allowed_actions=sorted(action.value for action in entry.actions),
        )


class ClinicianAgendaOut(Schema):
    appointments: list[ClinicianEntryOut]


class AdminEntryOut(Schema):
    id: UUID
    status: str
    source: str
    start: str
    end: str
    time_zone: str
    reason: str | None
    patient: UUID
    patient_name: str
    clinician: UUID
    clinician_name: str
    hospital_name: str
    department: str
    type: str
    room: str | None

    @staticmethod
    def of(row: AdminAppointmentRow) -> "AdminEntryOut":
        appointment = row.appointment
        return AdminEntryOut(
            id=appointment.id.value,
            status=appointment.status.value,
            source=appointment.source.value,
            start=appointment.start.isoformat(),
            end=appointment.end.isoformat(),
            time_zone=row.time_zone,
            reason=appointment.reason,
            patient=appointment.patient_id.value,
            patient_name=row.patient_name,
            clinician=appointment.clinician_id.value,
            clinician_name=row.clinician_name,
            hospital_name=row.hospital_name,
            department=row.department,
            type=row.appointment_type,
            room=row.room,
        )


class AdminAgendaOut(Schema):
    items: list[AdminEntryOut]
    total: int
    page: int


Listed = AgendaOut | ClinicianAgendaOut | AdminAgendaOut


@router.get("/appointments", response=Listed, auth=None)
def list_own(request: HttpRequest, query: Query[AgendaQuery]) -> Listed:
    identity = current_identity(request)
    listed = container().list_appointments_as_caller.execute(
        actor_id=identity.user_id,
        query=AppointmentsQuery(
            clinician_id=_optional_id(query.clinician),
            patient_id=_optional_id(query.patient),
            status=query.status,
            start=query.start,
            end=query.end,
            department_id=_optional_id(query.department),
            source=query.source,
            page=query.page,
        ),
    )
    if isinstance(listed, Page):
        return AdminAgendaOut(
            items=[AdminEntryOut.of(row) for row in listed.items],
            total=listed.total,
            page=listed.number,
        )
    if isinstance(listed, ClinicianAppointments):
        return ClinicianAgendaOut(appointments=[ClinicianEntryOut.of(e) for e in listed.entries])
    return AgendaOut(
        upcoming=[AgendaEntryOut.of(e) for e in listed.upcoming],
        past=[AgendaEntryOut.of(e) for e in listed.past],
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
    cancelled = container().cancel_appointment.execute(
        appointment_id=Id(appointment_id), actor_id=identity.user_id, reason=payload.reason
    )
    return AppointmentOut.of(cancelled)


@router.post("/appointments/{appointment_id}/reschedule", response=AppointmentOut, auth=None)
def reschedule(request: HttpRequest, appointment_id: UUID, payload: RescheduleIn) -> AppointmentOut:
    identity = current_identity(request)
    moved = container().reschedule_appointment.execute(
        appointment_id=Id(appointment_id), actor_id=identity.user_id, start=payload.start
    )
    return AppointmentOut.of(moved)


@router.post("/appointments/{appointment_id}/check-in", response=AppointmentOut, auth=None)
def check_in(request: HttpRequest, appointment_id: UUID) -> AppointmentOut:
    identity = current_identity(request)
    changed = container().check_in_appointment.execute(
        actor_id=identity.user_id, appointment_id=Id(appointment_id)
    )
    return AppointmentOut.of(changed)


@router.post("/appointments/{appointment_id}/complete", response=AppointmentOut, auth=None)
def complete(request: HttpRequest, appointment_id: UUID) -> AppointmentOut:
    identity = current_identity(request)
    changed = container().complete_appointment.execute(
        actor_id=identity.user_id, appointment_id=Id(appointment_id)
    )
    return AppointmentOut.of(changed)


@router.post("/appointments/{appointment_id}/no-show", response=AppointmentOut, auth=None)
def no_show(request: HttpRequest, appointment_id: UUID) -> AppointmentOut:
    identity = current_identity(request)
    changed = container().mark_no_show.execute(
        actor_id=identity.user_id, appointment_id=Id(appointment_id)
    )
    return AppointmentOut.of(changed)
