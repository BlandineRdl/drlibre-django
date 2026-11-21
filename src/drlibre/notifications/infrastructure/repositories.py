from django.db import IntegrityError, transaction

from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.notifications.domain.notification import Notification, NotificationKind
from drlibre.notifications.infrastructure.django.models import REMINDER_UNIQUE, NotificationRecord
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest


def _notification(row: NotificationRecord) -> Notification:
    return Notification(
        id=Id(row.id),
        recipient_id=Id(row.recipient_id),
        kind=NotificationKind(row.kind),
        title=row.title,
        body=row.body,
        appointment_id=Id(row.appointment_id) if row.appointment_id else None,
        created_at=row.created_at,
        read_at=row.read_at,
    )


def _fields(notification: Notification) -> dict[str, object]:
    appointment = notification.appointment_id
    return {
        "recipient_id": notification.recipient_id.value,
        "kind": notification.kind.value,
        "title": notification.title,
        "body": notification.body,
        "appointment_id": appointment.value if appointment else None,
        "created_at": notification.created_at,
        "read_at": notification.read_at,
    }


class DjangoNotifications(Notifications):
    def add(self, notification: Notification) -> bool:
        try:
            # A savepoint, so a second reminder leaves the caller's transaction usable.
            with transaction.atomic():
                NotificationRecord.objects.create(id=notification.id.value, **_fields(notification))
        except IntegrityError as error:
            name = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
            if name != REMINDER_UNIQUE:
                raise
            return False
        return True

    def page_for(self, recipient_id: Id, request: PageRequest) -> Page[Notification]:
        rows = NotificationRecord.objects.filter(recipient_id=recipient_id.value)
        page = rows.order_by("-created_at", "-id")[request.offset : request.offset + PAGE_SIZE]
        return Page(
            items=tuple(_notification(row) for row in page),
            total=rows.count(),
            number=request.number,
        )

    def get(self, notification_id: Id) -> Notification | None:
        row = NotificationRecord.objects.filter(id=notification_id.value).first()
        return _notification(row) if row else None

    def save(self, notification: Notification) -> None:
        updated = NotificationRecord.objects.filter(id=notification.id.value).update(
            **_fields(notification)
        )
        if not updated:
            raise DomainError(ErrorCode.NOT_FOUND, "Notification introuvable.")

    def unread_count(self, recipient_id: Id) -> int:
        return NotificationRecord.objects.filter(
            recipient_id=recipient_id.value, read_at__isnull=True
        ).count()

    def reminded_among(self, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        rows = NotificationRecord.objects.filter(
            kind=NotificationKind.APPOINTMENT_REMINDER.value,
            appointment_id__in=[i.value for i in appointment_ids],
        )
        return frozenset(Id(value) for value in rows.values_list("appointment_id", flat=True))
