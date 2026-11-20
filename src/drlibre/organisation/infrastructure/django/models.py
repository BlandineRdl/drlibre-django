import uuid

from django.db import models


class HospitalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    street = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    time_zone = models.CharField(max_length=64)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.code


class SpecialtyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.code


class DepartmentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        HospitalRecord, on_delete=models.PROTECT, related_name="departments"
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.code


class RoomRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(DepartmentRecord, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True)
    floor = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField()
    equipment = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.code


class AppointmentTypeRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        DepartmentRecord, on_delete=models.PROTECT, related_name="appointment_types"
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True)
    duration_minutes = models.PositiveIntegerField()
    buffer_minutes = models.PositiveIntegerField()
    colour = models.CharField(max_length=7)
    needs_room = models.BooleanField()
    bookable_online = models.BooleanField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.code


class ClinicianProfileRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Identity owns users; contexts share no foreign key, only the id.
    user_id = models.UUIDField(unique=True)
    department = models.ForeignKey(
        DepartmentRecord, on_delete=models.PROTECT, related_name="clinicians"
    )
    specialty = models.ForeignKey(
        SpecialtyRecord, on_delete=models.PROTECT, related_name="clinicians"
    )
    title = models.CharField(max_length=100, db_index=True)
    bio = models.TextField(blank=True)
    default_room = models.ForeignKey(
        RoomRecord, on_delete=models.PROTECT, null=True, related_name="default_for"
    )
    weight = models.PositiveIntegerField(default=1)
    last_assigned_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.title
