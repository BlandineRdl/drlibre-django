from datetime import datetime

from drlibre.notifications.application.ports.inbound import AppointmentEvent, Notify
from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.notifications.domain.notification import Notification
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class NotifyUseCase(Notify):
    def __init__(self, *, clock: Clock, notifications: Notifications) -> None:
        self._clock = clock
        self._notifications = notifications

    def execute(
        self,
        *,
        event: AppointmentEvent,
        recipient_id: Id,
        appointment_id: Id,
        start: datetime,
        zone_name: str,
    ) -> bool:
        return self._notifications.add(
            Notification.for_event(
                event=event,
                recipient_id=recipient_id,
                appointment_id=appointment_id,
                start=start,
                zone_name=zone_name,
                at=self._clock.now(),
            )
        )
