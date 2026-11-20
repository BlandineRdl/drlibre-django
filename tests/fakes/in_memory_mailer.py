from drlibre.notifications.application.ports.outbound import EmailMessage, Mailer


class InMemoryMailer(Mailer):
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)
