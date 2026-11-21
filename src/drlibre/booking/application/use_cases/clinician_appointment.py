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
)
from drlibre.booking.application.use_cases.clinician_read_helpers import (
    time_zone_of,
    with_actions,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import (
    clinician_profile,
    own_clinician_appointment,
)
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


def _age(birth: date | None, today: date) -> int | None:
    if birth is None:
        return None
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _actor(entry_actor: Id | None, appointment: Appointment, clinician_user: Id) -> HistoryActor:
    if entry_actor == appointment.patient_id:
        return HistoryActor.PATIENT
    if entry_actor == clinician_user:
        return HistoryActor.CLINICIAN
    return HistoryActor.STAFF


class ClinicianAppointmentUseCase(ClinicianAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: BookingDirectory,
        appointments: Appointments,
        agenda: ClinicianAgenda,
        history: AppointmentHistory,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._appointments = appointments
        self._agenda = agenda
        self._history = history

    def execute(self, *, actor_id: Id, appointment_id: Id) -> AppointmentFile:
        profile_id = clinician_profile(self._directory, actor_id)
        own_clinician_appointment(self._appointments, appointment_id, profile_id)
        entry = self._agenda.detail(appointment_id)
        if entry is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
        time_zone = time_zone_of(self._directory, profile_id)
        today = self._clock.now().astimezone(ZoneInfo(time_zone)).date()
        # The guard proved the actor is the appointment's clinician user.
        history = tuple(
            HistoryLine(h.action, _actor(h.actor_id, entry.appointment, actor_id), h.at)
            for h in self._history.entries_of(appointment_id)
        )
        return AppointmentFile(
            entry=with_actions(entry),
            time_zone=time_zone,
            patient_age=_age(entry.patient_birth_date, today),
            history=history,
        )
