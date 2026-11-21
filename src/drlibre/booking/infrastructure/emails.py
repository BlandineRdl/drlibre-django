from datetime import datetime
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.outbound import Venue
from drlibre.notifications.application.ports.outbound import EmailMessage
from drlibre.shared_kernel.booking_policy import CODE_LIFETIME


def code_email(*, to: str, code: str) -> EmailMessage:
    """The code only: no appointment detail, no link that signs anyone in."""
    minutes = int(CODE_LIFETIME.total_seconds() // 60)
    body = f"Votre code de vérification : {code}\n\nIl est valable {minutes} minutes."
    return EmailMessage(to=(to,), subject="Votre code de vérification", body=body)


def appointment_email(
    *, to: str, subject: str, headline: str, start: datetime, venue: Venue, sign_in_url: str
) -> EmailMessage:
    """Time, hospital and provider; never the reason, and only a link to the sign-in page."""
    local = start.astimezone(ZoneInfo(venue.time_zone))
    when = f"{local:%d/%m/%Y à %H:%M} ({venue.time_zone})"
    body = (
        f"{headline}\n\n"
        f"Date : {when}\n"
        f"Hôpital : {venue.hospital_name}\n"
        f"Praticien : {venue.provider_name}\n\n"
        f"Retrouvez vos rendez-vous après connexion : {sign_in_url}"
    )
    return EmailMessage(to=(to,), subject=subject, body=body)


# Subject and headline of each appointment email.
CONFIRMED = ("Confirmation de votre rendez-vous", "Votre rendez-vous est confirmé.")
RESCHEDULED = ("Votre rendez-vous est déplacé", "Votre rendez-vous a été déplacé.")
CANCELLED = ("Votre rendez-vous est annulé", "Votre rendez-vous a été annulé.")
REMINDER = ("Rappel de votre rendez-vous", "Rappel : votre rendez-vous approche.")
