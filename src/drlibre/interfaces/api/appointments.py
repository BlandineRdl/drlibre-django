from uuid import UUID

from django.http import HttpRequest
from ninja import Query, Router, Schema, Status
from pydantic import AwareDatetime, ConfigDict, Field

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AgendaFilter,
    AppointmentStatus,
    ClinicianEntry,
    ClinicianFilter,
)
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity, Role
from drlibre.interfaces.api.booking import AppointmentOut
from drlibre.interfaces.web.auth import current_identity
from drlibre.shared_kernel.ids import Id

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


def _clinician_agenda(identity: Identity, query: AgendaQuery) -> ClinicianAgendaOut:
    # A clinician sees only their own calendar, so a `clinician` parameter changes nothing.
    entries = container().list_clinician_appointments.execute(
        actor_id=identity.user_id,
        agenda_filter=ClinicianFilter(
            patient_id=_optional_id(query.patient),
            status=query.status,
            start=query.start,
            end=query.end,
        ),
    )
    return ClinicianAgendaOut(appointments=[ClinicianEntryOut.of(e) for e in entries])


@router.get("/appointments", response=AgendaOut | ClinicianAgendaOut, auth=None)
def list_own(request: HttpRequest, query: Query[AgendaQuery]) -> AgendaOut | ClinicianAgendaOut:
    identity = current_identity(request)
    if identity.role is Role.CLINICIAN:
        return _clinician_agenda(identity, query)
    # A patient sees only their own appointments, so a `patient` parameter changes nothing.
    agenda = container().list_patient_appointments.execute(
        patient_id=identity.user_id,
        agenda_filter=AgendaFilter(
            clinician_id=_optional_id(query.clinician),
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
