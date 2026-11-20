from django.conf import settings
from django.core import mail

from drlibre.notifications.application.ports.outbound import EmailMessage, Mailer


class SmtpMailer(Mailer):
    def __init__(self, alias: str = "default") -> None:
        self._alias = alias

    def send(self, message: EmailMessage) -> None:
        mail.EmailMessage(
            subject=message.subject,
            body=message.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=list(message.to),
        ).send(using=self._alias)
