import structlog

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.django.models import AuditEntryRecord


class DjangoAuditLog(AuditLog):
    def record(self, entry: AuditEntry) -> None:
        AuditEntryRecord.objects.create(
            actor_id=entry.actor.value if entry.actor else None,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id.value if entry.entity_id else None,
            metadata=dict(entry.metadata),
            at=entry.at,
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        )
