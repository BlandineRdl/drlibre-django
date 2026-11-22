from dataclasses import replace
from datetime import date
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    AppointmentFile,
    ClinicianAppointment,
    HistoryActor,
    HistoryLine,
)
from drlibre.booking.application.ports.outbound import (
    AppointmentHistory,
    Appointments,
    BookingDirectory,
    ClinicianAgenda,
    Staff,
)
from drlibre.booking.application.use_cases.actor_scope import (
    ActorKind,
    actor_scope,
    scoped_appointment,
)
from drlibre.booking.application.use_cases.clinician_read_helpers import (
    with_actions,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import CLINICIANS_ONLY
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


def _age(birth: date | None, today: date) -> int | None:
    if birth is None:
        return None
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _actor(
    entry_actor: Id | None, appointment: Appointment, clinician_user: Id | None
) -> HistoryActor:
    if entry_actor == appointment.patient_id:
        return HistoryActor.PATIENT
    if clinician_user is not None and entry_actor == clinician_user:
        return HistoryActor.CLINICIAN
    return HistoryActor.STAFF


class ClinicianAppointmentUseCase(ClinicianAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: BookingDirectory,
        staff: Staff,
        appointments: Appointments,
        agenda: ClinicianAgenda,
        history: AppointmentHistory,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._staff = staff
        self._appointments = appointments
        self._agenda = agenda
        self._history = history

    def execute(self, *, actor_id: Id, appointment_id: Id) -> AppointmentFile:
        scope = actor_scope(self._directory, self._staff, actor_id)
        if scope.is_patient:
            raise DomainError(ErrorCode.FORBIDDEN, CLINICIANS_ONLY)
        found = scoped_appointment(scope, self._appointments, appointment_id)
        entry = self._agenda.detail(appointment_id)
        if entry is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
        is_admin = scope.kind is ActorKind.ADMIN
        if is_admin:
            # Clinical notes stay the clinician's alone (spec 3.1).
            entry = replace(entry, appointment=replace(entry.appointment, clinical_notes=None))
        venue = self._directory.venue(found.clinician_id)
        if venue is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
        time_zone = venue.time_zone
        today = self._clock.now().astimezone(ZoneInfo(time_zone)).date()
        # A clinician passed the guard as the appointment's clinician user.
        clinician_user = None if is_admin else actor_id
        history = tuple(
            HistoryLine(h.action, _actor(h.actor_id, entry.appointment, clinician_user), h.at)
            for h in self._history.entries_of(appointment_id)
        )
        return AppointmentFile(
            entry=with_actions(entry),
            time_zone=time_zone,
            patient_age=_age(entry.patient_birth_date, today),
            history=history,
            clinician_name=venue.provider_name,
            hospital_name=venue.hospital_name,
        )
