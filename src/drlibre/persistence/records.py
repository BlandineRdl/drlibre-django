from typing import Any

from django.db import models
from django.utils import timezone

from drlibre.persistence.provenance import acting_user_id


class TrackedQuerySet(models.QuerySet):
    def update(self, **kwargs: Any) -> int:
        # A bulk update skips `auto_now`: stamp it here unless the caller sets it.
        kwargs.setdefault("updated_at", timezone.now())
        return super().update(**kwargs)


class TrackedRecord(models.Model):
    """Spec §3: creation time, last update time and the signed-in creator, if any."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    # Identity owns users; contexts share no foreign key, only the id.
    created_by = models.UUIDField(null=True, editable=False, default=acting_user_id)

    objects = TrackedQuerySet.as_manager()

    class Meta:
        abstract = True
