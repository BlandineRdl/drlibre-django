# SQL is composed from fixed fragments only; every value is a bound parameter.
from typing import Any

from drlibre.interop.application.ports.inbound import (
    AuditAction,
    AuditDetail,
    AuditEventFilter,
    AuditEventQueries,
    AuditEventRow,
    Paging,
    Reader,
)
from drlibre.interop.domain.reader import admin_only
from drlibre.interop.infrastructure.sql_directory import Row, Where, loaded, page_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

_EVENTS = """
SELECT a.id, a.actor_id, actor.role AS actor_role, a.action, a.entity_type, a.entity_id,
       target.role AS entity_role, a.metadata, a.at, a.correlation_id
FROM audit_auditentryrecord a
LEFT JOIN identity_userrecord actor ON actor.id = a.actor_id
LEFT JOIN identity_userrecord target ON a.entity_type = 'user' AND target.id = a.entity_id
"""

# AuditAction.of in SQL: the suffix of the product action.
_SUFFIXES = {"created": "%.created", "updated": "%.updated", "deleted": "%.deleted"}
_ACTIONS = {
    AuditAction.CREATE: "o.action LIKE %(created)s",
    AuditAction.UPDATE: "o.action LIKE %(updated)s",
    AuditAction.DELETE: "o.action LIKE %(deleted)s",
    AuditAction.READ: "false",
    AuditAction.EXECUTE: (
        "o.action NOT LIKE %(created)s AND o.action NOT LIKE %(updated)s"
        " AND o.action NOT LIKE %(deleted)s"
    ),
}


def _detail(value: Any) -> AuditDetail:
    return tuple(map(str, value)) if isinstance(value, list) else value


def _row(r: Row) -> AuditEventRow:
    metadata = tuple((k, _detail(v)) for k, v in sorted(loaded(r["metadata"]).items()))
    return AuditEventRow(
        Id(r["id"]), Id(r["actor_id"]) if r["actor_id"] else None, r["actor_role"], r["action"],
        r["entity_type"], Id(r["entity_id"]) if r["entity_id"] else None, r["entity_role"],
        metadata, r["at"], r["correlation_id"],
    )  # fmt: skip


class SqlAuditEventQueries(AuditEventQueries):
    def events(
        self, criteria: AuditEventFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AuditEventRow]:
        admin_only(reader)
        where = Where(criteria.ids)
        where.when(criteria.agent, "o.actor_id = %(agent)s", "agent")
        where.when(criteria.entity, "o.entity_id = %(entity)s", "entity")
        where.when(criteria.entity_type, "o.entity_type = %(entity_type)s", "entity_type")
        if criteria.actions:
            either = " OR ".join(f"({_ACTIONS[a]})" for a in criteria.actions)
            where.add(f"({either})", **_SUFFIXES)
        where.when(criteria.at_from, "o.at >= %(at_from)s", "at_from")
        where.when(criteria.at_before, "o.at < %(at_before)s", "at_before")
        rows, total = page_of(_EVENTS, where, paging, ("at", "id"))
        return Page(tuple(map(_row, rows)), total, paging.page if paging else 1)
