from datetime import datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id

__all__ = ["Appointment", "BookAppointment"]


class BookAppointment(Protocol):
    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        """Book for the signed-in patient, the first available clinician when none is named.

        Refused with not_found, conflict, rule_violation, no_room_available or
        no_clinician_available, writing nothing; the end time and the room are never accepted.
        """
        ...
