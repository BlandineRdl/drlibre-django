import uuid

from django.db import models

from drlibre.persistence.records import TrackedRecord


class UserRecord(TrackedRecord):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=254, unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    password_hash = models.CharField(max_length=256, null=True)  # noqa: DJ001
    must_change_password = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True)
    phone = models.CharField(max_length=30, null=True)  # noqa: DJ001
    birth_date = models.DateField(null=True)
    email_verified_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        indexes = (models.Index(fields=["full_name"]),)

    def __str__(self) -> str:
        return str(self.id)


class SessionRecord(TrackedRecord):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="sessions")
    expires_at = models.DateTimeField()
    lifetime = models.DurationField()
    extendable = models.BooleanField()
    user_agent = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return str(self.id)


class SignInLinkRecord(TrackedRecord):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    patient = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="sign_in_links")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)

    def __str__(self) -> str:
        return str(self.id)
