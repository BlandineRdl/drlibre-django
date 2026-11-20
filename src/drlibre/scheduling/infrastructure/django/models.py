import uuid

from django.db import models


class AvailabilityRuleModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # A profile without appointments may be deleted (spec 10); its rules go with it.
    clinician = models.ForeignKey(
        "organisation.ClinicianProfileRecord",
        on_delete=models.CASCADE,
        related_name="availability_rules",
    )
    weekday = models.PositiveSmallIntegerField()
    start = models.TimeField()
    end = models.TimeField()
    step_minutes = models.PositiveSmallIntegerField()
    room = models.ForeignKey(
        "organisation.RoomRecord",
        on_delete=models.PROTECT,
        null=True,
        related_name="availability_rules",
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True)
    clinician_id: uuid.UUID
    room_id: uuid.UUID | None

    def __str__(self) -> str:
        return f"{self.weekday} {self.start}-{self.end}"


class TimeOffModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinician = models.ForeignKey(
        "organisation.ClinicianProfileRecord", on_delete=models.CASCADE, related_name="time_offs"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    clinician_id: uuid.UUID

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"
