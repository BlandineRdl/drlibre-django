from typing import Any

from celery import Celery, current_app
from django.db import transaction

from drlibre.notifications.application.email_task import REDACTED, SEND_EMAIL_TASK
from drlibre.notifications.application.ports.outbound import EmailMessage, EmailOutbox


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
