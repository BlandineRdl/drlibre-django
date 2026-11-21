from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.notifications.application.ports.inbound import MarkNotificationRead, Notification
from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class MarkNotificationReadUseCase(MarkNotificationRead):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, notifications: Notifications
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._notifications = notifications

    def execute(self, *, user_id: Id, notification_id: Id) -> Notification:
        with self._uow:
            notification = self._notifications.get(notification_id)
            if notification is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Notification introuvable.")
            if notification.recipient_id != user_id:
                raise DomainError(ErrorCode.FORBIDDEN, "Cette notification n'est pas la vôtre.")
            if notification.is_read:
                return notification
            now = self._clock.now()
            read = notification.mark_read(now)
            self._notifications.save(read)
            self._audit.record(
                AuditEntry.from_event(
                    actor=user_id,
                    action="notification.read",
                    entity_type="notification",
                    entity_id=read.id,
                    at=now,
                    metadata={"kind": read.kind},
                )
            )
            return read
