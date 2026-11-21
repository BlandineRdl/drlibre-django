from drlibre.audit.application.ports.inbound import AuditQueries, AuditRecordView
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.shared_kernel.ids import Id


class DjangoAuditQueries(AuditQueries):
    def has_acted(self, actor: Id) -> bool:
        return AuditEntryRecord.objects.filter(actor_id=actor.value).exists()

    def entries_for(self, entity_type: str, entity_id: Id) -> tuple[AuditRecordView, ...]:
        rows = AuditEntryRecord.objects.filter(
            entity_type=entity_type, entity_id=entity_id.value
        ).order_by("at", "id")
        return tuple(
            AuditRecordView(
                actor_id=Id(row.actor_id) if row.actor_id else None, action=row.action, at=row.at
            )
            for row in rows
        )
