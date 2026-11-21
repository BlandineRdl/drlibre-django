import uuid

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

INACTIVE_STATUSES = ("CANCELLED", "NO_SHOW")
STATUSES = ("BOOKED", "CHECKED_IN", "COMPLETED", *INACTIVE_STATUSES)


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


def _no_overlap(name: str, column: str) -> ExclusionConstraint:
    return ExclusionConstraint(
        name=name,
        expressions=(
            (TsTzRange("start", "end", RangeBoundary()), RangeOperators.OVERLAPS),
            (column, RangeOperators.EQUAL),
        ),
        condition=~Q(status__in=INACTIVE_STATUSES),
    )


class AppointmentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Identity owns users; contexts share no foreign key, only the id.
    patient_id = models.UUIDField()
    clinician = models.ForeignKey(
        "organisation.ClinicianProfileRecord",
        on_delete=models.PROTECT,
        db_index=False,
        related_name="appointments",
    )
    appointment_type = models.ForeignKey(
        "organisation.AppointmentTypeRecord", on_delete=models.PROTECT, related_name="appointments"
    )
    room = models.ForeignKey(
        "organisation.RoomRecord", on_delete=models.PROTECT, null=True, related_name="appointments"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=20)
    source = models.CharField(max_length=20)
    reason = models.CharField(max_length=500, null=True)  # noqa: DJ001
    cancelled_at = models.DateTimeField(null=True)
    cancellation_reason = models.CharField(max_length=500, null=True)  # noqa: DJ001
    clinician_id: uuid.UUID
    appointment_type_id: uuid.UUID
    room_id: uuid.UUID | None

    class Meta:
        indexes = (
            models.Index(fields=("clinician", "start"), name="appointment_clinician_start"),
            models.Index(fields=("patient_id", "start"), name="appointment_patient_start"),
            models.Index(fields=("room", "start"), name="appointment_room_start"),
        )
        constraints = (
            _no_overlap("appointment_clinician_no_overlap", "clinician"),
            _no_overlap("appointment_patient_no_overlap", "patient_id"),
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="appointment_end_after_start"
            ),
            models.CheckConstraint(
                condition=Q(status__in=STATUSES), name="appointment_status_known"
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="CANCELLED",
                        cancelled_at__isnull=False,
                        cancellation_reason__isnull=False,
                    )
                    | Q(
                        ~Q(status="CANCELLED"),
                        cancelled_at__isnull=True,
                        cancellation_reason__isnull=True,
                    )
                ),
                name="appointment_cancellation_consistent",
            ),
        )

    def __str__(self) -> str:
        return str(self.id)


class BookingHoldRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # A hold is short-lived: it goes with its clinician or type rather than blocking their deletion.
    clinician = models.ForeignKey(
        "organisation.ClinicianProfileRecord",
        on_delete=models.CASCADE,
        db_index=False,
        related_name="booking_holds",
    )
    appointment_type = models.ForeignKey(
        "organisation.AppointmentTypeRecord",
        on_delete=models.CASCADE,
        related_name="booking_holds",
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    source = models.CharField(max_length=20)
    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    email = models.CharField(max_length=254)
    phone = models.CharField(max_length=30, null=True)  # noqa: DJ001
    reason = models.CharField(max_length=500, null=True)  # noqa: DJ001
    expires_at = models.DateTimeField()
    clinician_id: uuid.UUID
    appointment_type_id: uuid.UUID

    class Meta:
        indexes = (
            models.Index(fields=("clinician", "start"), name="hold_clinician_start"),
            models.Index(fields=("email", "expires_at"), name="hold_email_expires"),
            models.Index(fields=("expires_at",), name="hold_expires"),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="booking_hold_end_after_start"
            ),
        )

    def __str__(self) -> str:
        return str(self.id)


class VerificationCodeRecord(models.Model):
    hold = models.OneToOneField(
        BookingHoldRecord, on_delete=models.CASCADE, primary_key=True, related_name="code"
    )
    email = models.CharField(max_length=254)
    purpose = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    hold_id: uuid.UUID

    def __str__(self) -> str:
        return str(self.hold_id)
