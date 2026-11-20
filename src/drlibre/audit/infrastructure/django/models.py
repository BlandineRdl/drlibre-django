import uuid
from typing import Any

from django.db import models


class AppendOnlyError(RuntimeError):
    pass


class AuditEntryRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(null=True, db_index=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField(null=True)
    metadata = models.JSONField(default=dict)
    at = models.DateTimeField(db_index=True)
    correlation_id = models.CharField(max_length=128, blank=True)

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type} {self.entity_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyError("audit entries are never changed")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise AppendOnlyError("audit entries are never deleted")
