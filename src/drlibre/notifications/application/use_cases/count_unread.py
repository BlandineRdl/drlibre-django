from drlibre.notifications.application.ports.inbound import CountUnread
from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.shared_kernel.ids import Id


class CountUnreadUseCase(CountUnread):
    def __init__(self, *, notifications: Notifications) -> None:
        self._notifications = notifications

    def execute(self, *, recipient_id: Id) -> int:
        return self._notifications.unread_count(recipient_id)
