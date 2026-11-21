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


def confirmation_email(*, to: str, start: datetime, venue: Venue, sign_in_url: str) -> EmailMessage:
    """Time, hospital and provider; never the reason, and only a link to the sign-in page."""
    local = start.astimezone(ZoneInfo(venue.time_zone))
    when = f"{local:%d/%m/%Y à %H:%M} ({venue.time_zone})"
    body = (
        "Votre rendez-vous est confirmé.\n\n"
        f"Date : {when}\n"
        f"Hôpital : {venue.hospital_name}\n"
        f"Praticien : {venue.provider_name}\n\n"
        f"Retrouvez vos rendez-vous après connexion : {sign_in_url}"
    )
    return EmailMessage(to=(to,), subject="Confirmation de votre rendez-vous", body=body)
