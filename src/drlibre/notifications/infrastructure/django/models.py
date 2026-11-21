import uuid

from django.db import models
from django.db.models import Q

from drlibre.persistence.records import TrackedRecord

REMINDER_UNIQUE = "notification_one_reminder_per_appointment"


class NotificationRecord(TrackedRecord):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Identity owns users and booking owns appointments; contexts share no foreign key.
    recipient_id = models.UUIDField()
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=300)
    appointment_id = models.UUIDField(null=True)
    created_at = models.DateTimeField()
    read_at = models.DateTimeField(null=True)
    time_zone = models.CharField(max_length=64, default="")

    class Meta:
        indexes = (
            models.Index(fields=("recipient_id", "-created_at"), name="notification_recipient"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("appointment_id",),
                condition=Q(kind="APPOINTMENT_REMINDER"),
                name=REMINDER_UNIQUE,
            ),
        )

    def __str__(self) -> str:
        return str(self.id)
