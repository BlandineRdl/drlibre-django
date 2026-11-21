from urllib.parse import urlencode

from drlibre.identity.application.ports.outbound import LinkNotices
from drlibre.identity.domain.sign_in_link import LINK_LIFETIME
from drlibre.notifications.application.ports.outbound import EmailMessage, EmailOutbox


def link_email(*, to: str, url: str) -> EmailMessage:
    """The one email that carries a link signing someone in."""
    minutes = int(LINK_LIFETIME.total_seconds() // 60)
    body = (
        f"Pour accéder à votre espace patient, ouvrez ce lien : {url}\n\n"
        f"Il est valable {minutes} minutes et ne sert qu'une fois."
    )
    return EmailMessage(to=(to,), subject="Votre lien de connexion", body=body)


class OutboxLinkNotices(LinkNotices):
    """Queues the link email, sent once the unit of work commits."""

    def __init__(self, *, outbox: EmailOutbox, public_base_url: str) -> None:
        self._outbox = outbox
        self._base = public_base_url.rstrip("/")

    def link_sent(self, *, email: str, token: str) -> None:
        url = f"{self._base}/sign-in/link?{urlencode({'token': token})}"
        self._outbox.queue(link_email(to=email, url=url))
