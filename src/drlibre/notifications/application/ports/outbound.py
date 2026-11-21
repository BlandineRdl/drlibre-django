from dataclasses import dataclass
from typing import Protocol

from drlibre.notifications.domain.notification import Notification
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


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


class Notifications(Protocol):
    def add(self, notification: Notification) -> bool:
        """Store it in the caller's unit of work; False, storing nothing, for a second reminder."""
        ...

    def page_for(self, recipient_id: Id, request: PageRequest) -> Page[Notification]:
        """The recipient's notifications, newest first, one page of 20."""
        ...

    def get(self, notification_id: Id) -> Notification | None:
        """The notification, or None when unknown."""
        ...

    def save(self, notification: Notification) -> None:
        """Replace the stored notification; an absent id is refused as not found."""
        ...

    def unread_count(self, recipient_id: Id) -> int:
        """How many of the recipient's notifications are unread."""
        ...
