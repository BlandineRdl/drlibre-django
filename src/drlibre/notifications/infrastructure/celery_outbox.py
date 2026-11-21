from typing import Any

from celery import Celery, current_app
from django.db import transaction

from drlibre.notifications.application.ports.outbound import EmailMessage, EmailOutbox

SEND_EMAIL_TASK = "drlibre.send_email"
# Worker logs print these instead of the arguments, which hold codes and sign-in links.
REDACTED = "[redacted]"


class CeleryEmailOutbox(EmailOutbox):
    """Enqueues each message by task name once the open transaction commits; none on rollback."""

    def __init__(self, app: Celery | None = None) -> None:
        self._app = app

    def queue(self, message: EmailMessage) -> None:
        payload = {"to": list(message.to), "subject": message.subject, "body": message.body}
        transaction.on_commit(lambda: self._send(payload))

    def _send(self, payload: dict[str, Any]) -> None:
        app = self._app or current_app
        app.send_task(  # pyrefly: ignore[not-callable]
            SEND_EMAIL_TASK, kwargs=payload, argsrepr=REDACTED, kwargsrepr=REDACTED
        )
