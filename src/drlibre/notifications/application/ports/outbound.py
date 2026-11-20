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
