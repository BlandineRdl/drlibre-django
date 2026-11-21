from drlibre.booking.application.ports.outbound import (
    BookingDirectory,
    BookingNotices,
    Patients,
    Venue,
)
from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.infrastructure import emails
from drlibre.notifications.application.ports.inbound import (
    AppointmentEvent,
    Notify,
    RemindedAppointments,
)
from drlibre.notifications.application.ports.outbound import EmailOutbox
from drlibre.shared_kernel.ids import Id


class OutboxBookingNotices(BookingNotices):
    """Writes the patient's in-app notification and queues the email sent once the unit commits."""

    def __init__(
        self,
        *,
        outbox: EmailOutbox,
        notify: Notify,
        reminded: RemindedAppointments,
        directory: BookingDirectory,
        patients: Patients,
        public_base_url: str,
    ) -> None:
        self._outbox = outbox
        self._notify = notify
        self._reminded = reminded
        self._directory = directory
        self._patients = patients
        self._sign_in_url = f"{public_base_url.rstrip('/')}/sign-in"

    def code_sent(self, *, email: str, code: str) -> None:
        self._outbox.queue(emails.code_email(to=email, code=code))

    def confirmed(self, appointment: Appointment) -> None:
        self._email(appointment, emails.CONFIRMED, self._venue(appointment))

    def booked(self, appointment: Appointment) -> None:
        self._in_app(appointment, AppointmentEvent.BOOKED, self._venue(appointment))

    def rescheduled(self, appointment: Appointment) -> None:
        venue = self._venue(appointment)
        self._in_app(appointment, AppointmentEvent.RESCHEDULED, venue)
        self._email(appointment, emails.RESCHEDULED, venue)

    def cancelled(self, appointment: Appointment) -> None:
        venue = self._venue(appointment)
        self._in_app(appointment, AppointmentEvent.CANCELLED, venue)
        self._email(appointment, emails.CANCELLED, venue)

    def reminded(self, appointment: Appointment) -> bool:
        venue = self._venue(appointment)
        if not self._in_app(appointment, AppointmentEvent.REMINDED, venue):
            return False
        self._email(appointment, emails.REMINDER, venue)
        return True

    def already_reminded(self, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        return self._reminded.execute(appointment_ids=appointment_ids)

    def _venue(self, appointment: Appointment) -> Venue | None:
        return self._directory.venue(appointment.clinician_id)

    def _in_app(
        self, appointment: Appointment, event: AppointmentEvent, venue: Venue | None
    ) -> bool:
        return self._notify.execute(
            event=event,
            recipient_id=appointment.patient_id,
            appointment_id=appointment.id,
            start=appointment.start,
            # An unknown clinician has no venue; the time is then shown in UTC.
            zone_name=venue.time_zone if venue else "UTC",
        )

    def _email(
        self, appointment: Appointment, wording: tuple[str, str], venue: Venue | None
    ) -> None:
        email = self._patients.email_of(appointment.patient_id)
        if email is None or venue is None:
            return
        subject, headline = wording
        self._outbox.queue(
            emails.appointment_email(
                to=email,
                subject=subject,
                headline=headline,
                start=appointment.start,
                venue=venue,
                sign_in_url=self._sign_in_url,
            )
        )
