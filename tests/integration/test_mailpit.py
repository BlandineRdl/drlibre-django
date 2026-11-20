import uuid

import pytest

from drlibre.notifications.application.ports.outbound import EmailMessage
from drlibre.notifications.infrastructure.smtp_mailer import SmtpMailer
from tests.mailpit import find_messages

pytestmark = pytest.mark.integration


def test_smtp_mailer_delivers_to_mailpit(mailpit_smtp: str) -> None:
    subject = f"walking skeleton {uuid.uuid4()}"

    SmtpMailer().send(EmailMessage(to=("visitor@example.test",), subject=subject, body="Ping"))

    [message] = find_messages(mailpit_smtp, subject)
    assert message["Subject"] == subject
    assert message["From"]["Address"] == "no-reply@drlibre.localhost"
