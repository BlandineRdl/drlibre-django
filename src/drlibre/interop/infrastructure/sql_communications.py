# SQL is composed from fixed fragments only; every value is a bound parameter.
from django.db import connection

from drlibre.interop.application.ports.inbound import (
    CommunicationFilter,
    CommunicationQueries,
    CommunicationRow,
    Paging,
    Reader,
)
from drlibre.interop.infrastructure.sql_directory import Row, Where, page_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

_COMMUNICATIONS = """
SELECT n.id, n.recipient_id, u.role AS recipient_role, n.kind, n.title, n.body,
       n.appointment_id, n.created_at AS sent, n.read_at AS received, n.updated_at
FROM notifications_notificationrecord n
LEFT JOIN identity_userrecord u ON u.id = n.recipient_id
"""

_EXISTS = "SELECT EXISTS (SELECT 1 FROM notifications_notificationrecord WHERE id = %(id)s)"


def _row(r: Row) -> CommunicationRow:
    appointment = Id(r["appointment_id"]) if r["appointment_id"] else None
    return CommunicationRow(
        Id(r["id"]), Id(r["recipient_id"]), r["recipient_role"], r["kind"], r["title"],
        r["body"], appointment, r["sent"], r["received"], r["updated_at"],
    )  # fmt: skip


class SqlCommunicationQueries(CommunicationQueries):
    def communications(
        self, criteria: CommunicationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[CommunicationRow]:
        where = Where(criteria.ids)
        me = reader.user_id.value if reader.user_id else None
        where.add("o.recipient_id = %(me)s" if me else "false", me=me)
        where.when(criteria.recipient, "o.recipient_id = %(recipient)s", "recipient")
        where.when(criteria.category, "o.kind = %(category)s", "category")
        where.when(criteria.sent_from, "o.sent >= %(sent_from)s", "sent_from")
        where.when(criteria.sent_before, "o.sent < %(sent_before)s", "sent_before")
        rows, total = page_of(_COMMUNICATIONS, where, paging, ("sent", "id"))
        return Page(tuple(map(_row, rows)), total, paging.page if paging else 1)

    def exists(self, communication_id: Id) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(_EXISTS, {"id": communication_id.value})
            row = cursor.fetchone()
        return bool(row and row[0])
