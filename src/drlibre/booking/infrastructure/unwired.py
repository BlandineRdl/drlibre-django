from datetime import datetime

from drlibre.booking.application.ports.inbound import BookAppointment
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id


class UnwiredBookAppointment(BookAppointment):
    """Stands in until the Django booking adapters exist (E3 phase 3); nothing exposes it yet."""

    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        raise NotImplementedError("Booking adapters are not wired yet.")
