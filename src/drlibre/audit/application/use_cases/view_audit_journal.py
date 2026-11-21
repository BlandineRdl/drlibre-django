from drlibre.audit.application.ports.inbound import (
    AuditFilter,
    AuditJournal,
    AuditQueries,
    AuditRow,
    JournalQuery,
    ViewAuditJournal,
)
from drlibre.audit.application.ports.outbound import JournalActors
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page


class ViewAuditJournalUseCase(ViewAuditJournal):
    def __init__(self, *, actors: JournalActors, queries: AuditQueries, time_zone: str) -> None:
        self._actors = actors
        self._queries = queries
        self._zone = time_zone

    def execute(self, *, actor_id: Id, query: JournalQuery) -> AuditJournal:
        if not self._actors.is_admin(actor_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Réservé aux administrateurs.")
        types = self._queries.entity_types()
        actor = self._actors.id_of(query.email) if query.email else None
        audit_filter = AuditFilter.from_query(
            actor_id=actor,
            entity_type=query.entity_type,
            start=query.start,
            end=query.end,
            time_zone=self._zone,
            entity_types=types,
        )
        # An email of no user matches no entry.
        page: Page[AuditRow] = (
            Page((), 0, 1)
            if query.email and actor is None
            else self._queries.page(audit_filter, query.request)
        )
        ids = frozenset(r.actor_id for r in page.items if r.actor_id is not None)
        return AuditJournal(page, audit_filter, types, self._actors.emails_of(ids))
