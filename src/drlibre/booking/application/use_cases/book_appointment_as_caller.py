from datetime import datetime

from drlibre.booking.application.ports.inbound import (
    BookAppointment,
    BookAppointmentAsCaller,
    BookForPatient,
)
from drlibre.booking.application.ports.outbound import BookingDirectory
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field


class BookAppointmentAsCallerUseCase(BookAppointmentAsCaller):
    def __init__(
        self,
        *,
        directory: BookingDirectory,
        book_appointment: BookAppointment,
        book_for_patient: BookForPatient,
    ) -> None:
        self._directory = directory
        self._book_appointment = book_appointment
        self._book_for_patient = book_for_patient

    def execute(
        self,
        *,
        actor_id: Id,
        appointment_type_id: Id,
        start: datetime,
        clinician_id: Id | None = None,
        patient_id: Id | None = None,
        room_id: Id | None = None,
    ) -> Appointment:
        if self._directory.clinician_of_user(actor_id) is not None:
            if patient_id is None:
                raise invalid_field("patient", "Indiquez le patient.")
            return self._book_for_patient.execute(
                actor_id=actor_id,
                patient_id=patient_id,
                appointment_type_id=appointment_type_id,
                start=start,
                room_id=room_id,
                clinician_id=clinician_id,
            )
        # A patient books for themself and never picks a room (spec 5.4).
        if room_id is not None or patient_id not in (None, actor_id):
            raise DomainError(
                ErrorCode.FORBIDDEN, "Seul le personnel choisit le patient ou la salle."
            )
        return self._book_appointment.execute(
            patient_id=actor_id,
            appointment_type_id=appointment_type_id,
            clinician_id=clinician_id,
            start=start,
        )
