import dataclasses

from drlibre.booking.application.ports.inbound import Appointment, ViewAppointment
from drlibre.booking.application.ports.outbound import Appointments
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


def own_appointment(appointments: Appointments, appointment_id: Id, patient_id: Id) -> Appointment:
    """The patient's own appointment; not_found when absent, forbidden for another patient."""
    appointment = appointments.get(appointment_id)
    if appointment is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
    if appointment.patient_id != patient_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Ce rendez-vous n'est pas le vôtre.")
    return appointment


class ViewAppointmentUseCase(ViewAppointment):
    def __init__(self, *, appointments: Appointments) -> None:
        self._appointments = appointments

    def execute(self, *, appointment_id: Id, patient_id: Id) -> Appointment:
        # Clinical notes are the clinician's alone.
        found = own_appointment(self._appointments, appointment_id, patient_id)
        return dataclasses.replace(found, clinical_notes=None)
