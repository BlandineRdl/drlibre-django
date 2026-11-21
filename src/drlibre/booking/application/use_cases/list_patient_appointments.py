import dataclasses

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AgendaFilter,
    AppointmentStatus,
    ListPatientAppointments,
    PatientAppointments,
)
from drlibre.booking.application.ports.outbound import PatientAgenda, Patients
from drlibre.booking.application.use_cases.require_patient import refuse_non_patient
from drlibre.booking.domain import booking_rules
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id

_UPCOMING = (AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN)


class ListPatientAppointmentsUseCase(ListPatientAppointments):
    def __init__(self, *, clock: Clock, patients: Patients, agenda: PatientAgenda) -> None:
        self._clock = clock
        self._patients = patients
        self._agenda = agenda

    def execute(self, *, patient_id: Id, agenda_filter: AgendaFilter) -> PatientAppointments:
        refuse_non_patient(self._patients, patient_id)
        now = self._clock.now()
        upcoming: list[AgendaEntry] = []
        past: list[AgendaEntry] = []
        for entry in self._agenda.entries(patient_id, agenda_filter):
            appointment = entry.appointment
            actions = booking_rules.allowed_actions(
                appointment, now, type_online=entry.bookable_online
            )
            filled = dataclasses.replace(entry, allowed_actions=actions)
            if appointment.status in _UPCOMING and appointment.start > now:
                upcoming.append(filled)
            else:
                past.append(filled)
        upcoming.sort(key=lambda e: e.appointment.start)
        past.sort(key=lambda e: e.appointment.start, reverse=True)
        return PatientAppointments(upcoming=tuple(upcoming), past=tuple(past))
