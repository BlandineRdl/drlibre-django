from datetime import datetime
from typing import Protocol

from drlibre.notifications.domain.notification import (
    AppointmentEvent,
    Notification,
    NotificationKind,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

__all__ = [
    "AppointmentEvent",
    "CountUnread",
    "ListNotifications",
    "MarkNotificationRead",
    "Notification",
    "NotificationKind",
    "Notify",
    "RemindedAppointments",
]


class Notify(Protocol):
    def execute(
        self,
        *,
        event: AppointmentEvent,
        recipient_id: Id,
        appointment_id: Id,
        start: datetime,
        zone_name: str,
    ) -> bool:
        """Write the notification in the caller's unit of work; False for a second reminder."""
        ...


class ListNotifications(Protocol):
    def execute(self, *, recipient_id: Id, request: PageRequest) -> Page[Notification]:
        """The caller's own notifications, newest first, one page of 20."""
        ...


class MarkNotificationRead(Protocol):
    def execute(self, *, user_id: Id, notification_id: Id) -> Notification:
        """Mark own notification read, audited; not_found if absent, forbidden if not own."""
        ...


class CountUnread(Protocol):
    def execute(self, *, recipient_id: Id) -> int:
        """How many of the caller's notifications are unread."""
        ...


class RemindedAppointments(Protocol):
    def execute(self, *, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        """Those of the appointments that already have a reminder."""
        ...
