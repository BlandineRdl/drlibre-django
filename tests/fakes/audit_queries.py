from drlibre.audit.application.ports.inbound import (
    AuditFilter,
    AuditQueries,
    AuditRecordView,
    AuditRow,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest
from tests.fakes.audit_log import InMemoryAuditLog


class InMemoryAuditQueries(AuditQueries):
    """Reads straight from the in-memory audit log."""

    def __init__(self, log: InMemoryAuditLog) -> None:
        self.log = log

    def _rows(self) -> list[AuditRow]:
        return [
            AuditRow(e.at, e.actor, e.action, e.entity_type, e.entity_id, correlation)
            for e, correlation in zip(self.log.entries, self.log.correlation_ids, strict=True)
        ]

    def has_acted(self, actor: Id) -> bool:
        return any(e.actor == actor for e in self.log.entries)

    def entries_for(self, entity_type: str, entity_id: Id) -> tuple[AuditRecordView, ...]:
        found = (
            e for e in self.log.entries if e.entity_type == entity_type and e.entity_id == entity_id
        )
        return tuple(
            AuditRecordView(e.actor, e.action, e.at) for e in sorted(found, key=lambda e: e.at)
        )

    def page(self, audit_filter: AuditFilter, request: PageRequest) -> Page[AuditRow]:
        f = audit_filter
        found = [
            r
            for r in self._rows()
            if f.actor_id in (None, r.actor_id)
            and f.entity_type in (None, r.entity_type)
            and (f.start is None or r.at >= f.start)
            and (f.end is None or r.at < f.end)
        ]
        # Newest first; the real adapter breaks ties on the row id, here on insertion order.
        found.sort(key=lambda r: r.at, reverse=True)
        window = tuple(found[request.offset : request.offset + PAGE_SIZE])
        return Page(window, len(found), request.number)

    def entity_types(self) -> tuple[str, ...]:
        return tuple(sorted({e.entity_type for e in self.log.entries}))
