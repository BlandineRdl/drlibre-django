import uuid

from django.db import models

from drlibre.persistence.records import TrackedRecord


class AvailabilityRuleModel(TrackedRecord):
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


class TimeOffModel(TrackedRecord):
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


class SlotModel(models.Model):
    # Derived cache, not a §3 record: no provenance columns.
    # Rebuilt per clinician by RefreshSlots; indexed for the department and clinician reads.
    clinician = models.ForeignKey(
        "organisation.ClinicianProfileRecord",
        on_delete=models.CASCADE,
        db_index=False,
        related_name="slots",
    )
    appointment_type = models.ForeignKey(
        "organisation.AppointmentTypeRecord",
        on_delete=models.CASCADE,
        db_index=False,
        related_name="slots",
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    clinician_id: uuid.UUID
    appointment_type_id: uuid.UUID

    class Meta:
        db_table = "scheduling_slot"
        indexes = (
            models.Index(fields=("appointment_type", "start"), name="slot_type_start"),
            models.Index(
                fields=("clinician", "appointment_type", "start"), name="slot_clinician_type_start"
            ),
        )

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"
