from drlibre.booking.application.emails import confirmation_email
from drlibre.booking.application.ports.outbound import BookingDirectory, BookingNotices, Patients
from drlibre.booking.domain.appointment import Appointment
from drlibre.notifications.application.ports.outbound import EmailOutbox


class OutboxBookingNotices(BookingNotices):
    """Queues the confirmation email, sent once the unit of work commits."""

    def __init__(
        self,
        *,
        outbox: EmailOutbox,
        directory: BookingDirectory,
        patients: Patients,
        public_base_url: str,
    ) -> None:
        self._outbox = outbox
        self._directory = directory
        self._patients = patients
        self._sign_in_url = f"{public_base_url.rstrip('/')}/sign-in"

    def confirmed(self, appointment: Appointment) -> None:
        email = self._patients.email_of(appointment.patient_id)
        venue = self._directory.venue(appointment.clinician_id)
        if email is None or venue is None:
            return
        self._outbox.queue(
            confirmation_email(
                to=email, start=appointment.start, venue=venue, sign_in_url=self._sign_in_url
            )
        )
