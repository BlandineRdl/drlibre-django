from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.notifications.domain.notification import Notification, NotificationKind
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest


class InMemoryNotifications(Notifications):
    def __init__(self) -> None:
        self.rows: list[Notification] = []

    def add(self, notification: Notification) -> bool:
        if notification.kind is NotificationKind.APPOINTMENT_REMINDER and any(
            row.kind is NotificationKind.APPOINTMENT_REMINDER
            and row.appointment_id == notification.appointment_id
            for row in self.rows
        ):
            return False
        self.rows.append(notification)
        return True

    def page_for(self, recipient_id: Id, request: PageRequest) -> Page[Notification]:
        own = [row for row in self.rows if row.recipient_id == recipient_id]
        own.sort(key=lambda row: (row.created_at, str(row.id)), reverse=True)
        items = own[request.offset : request.offset + PAGE_SIZE]
        return Page(items=tuple(items), total=len(own), number=request.number)

    def get(self, notification_id: Id) -> Notification | None:
        return next((row for row in self.rows if row.id == notification_id), None)

    def save(self, notification: Notification) -> None:
        for index, row in enumerate(self.rows):
            if row.id == notification.id:
                self.rows[index] = notification
                return
        raise DomainError(ErrorCode.NOT_FOUND, "Notification introuvable.")

    def unread_count(self, recipient_id: Id) -> int:
        return sum(1 for row in self.rows if row.recipient_id == recipient_id and not row.is_read)

    def reminded_among(self, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        return frozenset(
            row.appointment_id
            for row in self.rows
            if row.kind is NotificationKind.APPOINTMENT_REMINDER
            and row.appointment_id in appointment_ids
        )
