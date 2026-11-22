from django.db import connection

from drlibre.audit.application.ports.inbound import (
    AuditFilter,
    AuditQueries,
    AuditRecordView,
    AuditRow,
)
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest

# Loose index scan on `audit_entry_target_at`: one index probe per distinct type.
_ENTITY_TYPES = """
WITH RECURSIVE kinds AS (
    (SELECT entity_type FROM audit_auditentryrecord ORDER BY entity_type LIMIT 1)
    UNION ALL
    SELECT (
        SELECT a.entity_type FROM audit_auditentryrecord a
        WHERE a.entity_type > k.entity_type ORDER BY a.entity_type LIMIT 1
    )
    FROM kinds k WHERE k.entity_type IS NOT NULL
)
SELECT entity_type FROM kinds WHERE entity_type IS NOT NULL
"""


def _audit_row(row: AuditEntryRecord) -> AuditRow:
    return AuditRow(
        at=row.at,
        actor_id=Id(row.actor_id) if row.actor_id else None,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=Id(row.entity_id) if row.entity_id else None,
        correlation_id=row.correlation_id,
    )


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

    def page(self, audit_filter: AuditFilter, request: PageRequest) -> Page[AuditRow]:
        f = audit_filter
        rows = AuditEntryRecord.objects.all()
        if f.actor_id is not None:
            rows = rows.filter(actor_id=f.actor_id.value)
        if f.entity_type is not None:
            rows = rows.filter(entity_type=f.entity_type)
        if f.start is not None:
            rows = rows.filter(at__gte=f.start)
        if f.end is not None:
            rows = rows.filter(at__lt=f.end)
        window = rows.order_by("-at", "id")[request.offset : request.offset + PAGE_SIZE]
        return Page(tuple(_audit_row(r) for r in window), rows.count(), request.number)

    def entity_types(self) -> tuple[str, ...]:
        with connection.cursor() as cursor:
            cursor.execute(_ENTITY_TYPES)
            return tuple(sorted(row[0] for row in cursor.fetchall()))
