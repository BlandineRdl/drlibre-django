import uuid
from collections.abc import Callable

import pytest

from drlibre.notifications.application.ports.outbound import EmailMessage, Mailer
from drlibre.notifications.infrastructure.smtp_mailer import SmtpMailer
from tests.fakes.in_memory_mailer import InMemoryMailer
from tests.mailpit import find_messages

type Inbox = Callable[[str], list[tuple[str, ...]]]


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="smtp", marks=pytest.mark.integration),
    ]
)
def mailer_and_inbox(request: pytest.FixtureRequest) -> tuple[Mailer, Inbox]:
    if request.param == "fake":
        fake = InMemoryMailer()
        return fake, lambda subject: [m.to for m in fake.sent if m.subject == subject]
    api_url = request.getfixturevalue("mailpit_smtp")

    def inbox(subject: str) -> list[tuple[str, ...]]:
        found = find_messages(api_url, subject)
        return [tuple(to["Address"] for to in message["To"]) for message in found]

    return SmtpMailer(), inbox


def test_sent_message_reaches_its_recipient(mailer_and_inbox: tuple[Mailer, Inbox]) -> None:
    mailer, inbox = mailer_and_inbox
    subject = f"contract {uuid.uuid4()}"

    mailer.send(EmailMessage(to=("patient@example.test",), subject=subject, body="Hello"))

    assert inbox(subject) == [("patient@example.test",)]
