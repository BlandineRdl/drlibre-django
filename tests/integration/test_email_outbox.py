import uuid
from collections.abc import Iterator

import pytest
from celery import Celery
from django.db import transaction

from drlibre.interfaces.jobs.tasks import send_email
from drlibre.notifications.application.ports.outbound import EmailMessage
from drlibre.notifications.infrastructure.celery_outbox import SEND_EMAIL_TASK, CeleryEmailOutbox
from tests.mailpit import find_messages

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

MESSAGE = EmailMessage(to=("visiteur@example.org",), subject="Votre code", body="Code : 123456")


@pytest.fixture
def broker() -> Iterator[Celery]:
    """A Celery app on an in-memory broker, to read what the outbox really publishes."""
    app = Celery("outbox-test", broker=f"memory://{uuid.uuid4().hex}")
    yield app
    app.close()


def queue_then_fail(outbox: CeleryEmailOutbox) -> None:
    with transaction.atomic():
        outbox.queue(MESSAGE)
        raise RuntimeError


def published(app: Celery) -> list[object]:
    found: list[object] = []
    with app.connection_for_read() as connection:
        queue = connection.SimpleQueue("celery")
        while True:
            try:
                found.append(queue.get(block=False))
            except queue.Empty:
                return found


def test_nothing_is_published_before_the_commit_and_one_message_after(broker: Celery) -> None:
    """Epic E3 : les emails ne partent qu'après la validation de la réservation."""
    outbox = CeleryEmailOutbox(broker)

    with transaction.atomic():
        outbox.queue(MESSAGE)
        assert published(broker) == []

    [sent] = published(broker)
    assert sent.headers["task"] == SEND_EMAIL_TASK  # type: ignore[attr-defined]
    assert sent.payload[1] == {  # type: ignore[attr-defined]
        "to": ["visiteur@example.org"],
        "subject": "Votre code",
        "body": "Code : 123456",
    }


def test_nothing_is_published_when_the_transaction_rolls_back(broker: Celery) -> None:
    """Epic E3 : une réservation annulée n'envoie aucun email."""
    outbox = CeleryEmailOutbox(broker)

    with pytest.raises(RuntimeError):
        queue_then_fail(outbox)

    assert published(broker) == []


def test_the_message_headers_never_carry_the_code(broker: Celery) -> None:
    """Décision du plan : les journaux du worker n'impriment ni code ni lien."""
    CeleryEmailOutbox(broker).queue(MESSAGE)

    [sent] = published(broker)
    headers = sent.headers  # type: ignore[attr-defined]
    assert "123456" not in f"{headers['argsrepr']} {headers['kwargsrepr']}"


def test_the_send_email_task_delivers_to_mailpit(mailpit_smtp: str) -> None:
    subject = f"Votre code {uuid.uuid4()}"

    send_email(to=["visiteur@example.org"], subject=subject, body="Code : 123456")

    [message] = find_messages(mailpit_smtp, subject)
    assert message["To"][0]["Address"] == "visiteur@example.org"
