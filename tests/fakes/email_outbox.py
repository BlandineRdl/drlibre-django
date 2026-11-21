from drlibre.notifications.application.ports.outbound import EmailMessage, EmailOutbox


class RecordingEmailOutbox(EmailOutbox):
    def __init__(self) -> None:
        self.queued: list[EmailMessage] = []

    def queue(self, message: EmailMessage) -> None:
        self.queued.append(message)
