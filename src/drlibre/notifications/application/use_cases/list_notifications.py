from drlibre.notifications.application.ports.inbound import ListNotifications, Notification
from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


class ListNotificationsUseCase(ListNotifications):
    def __init__(self, *, notifications: Notifications) -> None:
        self._notifications = notifications

    def execute(self, *, recipient_id: Id, request: PageRequest) -> Page[Notification]:
        return self._notifications.page_for(recipient_id, request)
