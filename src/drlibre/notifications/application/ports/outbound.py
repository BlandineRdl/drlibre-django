from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: tuple[str, ...]
    subject: str
    body: str


class Mailer(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Deliver the message or raise; never swallow a failure."""
        ...


class EmailOutbox(Protocol):
    def queue(self, message: EmailMessage) -> None:
        """Keep the message for delivery once the caller's unit of work commits."""
        ...
