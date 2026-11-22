# SQL is composed from fixed fragments only; every value is a bound parameter.
from django.db import connection

from drlibre.interop.application.ports.inbound import (
    AppointmentResponseFilter,
    AppointmentResponseQueries,
    AppointmentResponseRow,
    Paging,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_directory import Where, page_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

_RESPONSES = """
SELECT w.id, w.patient_id, w.updated_at
FROM booking_waitlistentryrecord w
WHERE w.status = 'BOOKED'
"""

_EXISTS = """
SELECT EXISTS (SELECT 1 FROM booking_waitlistentryrecord WHERE id = %(id)s AND status = 'BOOKED')
"""

_SCOPES = {
    ReaderKind.PATIENT: "o.patient_id = %(me)s",
    ReaderKind.ADMIN: "true",
    ReaderKind.CLINICIAN: "false",
    ReaderKind.ANONYMOUS: "false",
}


class SqlAppointmentResponseQueries(AppointmentResponseQueries):
    def responses(
        self, criteria: AppointmentResponseFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AppointmentResponseRow]:
        where = Where(criteria.ids)
        where.add(_SCOPES[reader.kind], me=reader.user_id.value if reader.user_id else None)
        where.when(criteria.patient, "o.patient_id = %(patient)s", "patient")
        rows, total = page_of(_RESPONSES, where, paging, ("updated_at", "id"))
        found = (
            AppointmentResponseRow(Id(r["id"]), Id(r["patient_id"]), r["updated_at"]) for r in rows
        )
        return Page(tuple(found), total, paging.page if paging else 1)

    def exists(self, response_id: Id) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(_EXISTS, {"id": response_id.value})
            row = cursor.fetchone()
        return bool(row and row[0])
