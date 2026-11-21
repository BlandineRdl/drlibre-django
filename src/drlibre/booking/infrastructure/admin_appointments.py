# SQL is composed from fixed fragments only; every value is a bound parameter.
from typing import Any

from django.db import connection

from drlibre.booking.application.ports.outbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    AdminAppointments,
    ExportRow,
)
from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.booking.infrastructure.patient_agenda import appointment_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest

_ROWS = """
SELECT a.id, a.patient_id, a.clinician_id, a.appointment_type_id, a.room_id, a.start, a."end",
       a.status, a.source, a.reason, a.cancelled_at, a.cancellation_reason,
       c.department_id, p.full_name AS patient_name, u.full_name AS clinician_name,
       d.name AS department, t.name AS appointment_type, r.name AS room,
       h.name AS hospital_name, h.time_zone
FROM booking_appointmentrecord a
JOIN identity_userrecord p ON p.id = a.patient_id
JOIN organisation_clinicianprofilerecord c ON c.id = a.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id
JOIN organisation_departmentrecord d ON d.id = c.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
JOIN organisation_appointmenttyperecord t ON t.id = a.appointment_type_id
LEFT JOIN organisation_roomrecord r ON r.id = a.room_id
WHERE (%(from)s::date IS NULL OR (a.start AT TIME ZONE h.time_zone)::date >= %(from)s::date)
  AND (%(to)s::date IS NULL OR (a.start AT TIME ZONE h.time_zone)::date <= %(to)s::date)
  -- Sargable bounds wider than any zone offset, so appointment_start can serve the range.
  AND (%(from)s::date IS NULL OR a.start >= %(from)s::date - interval '1 day')
  AND (%(to)s::date IS NULL OR a.start < %(to)s::date + interval '2 days')
  AND (%(department)s::uuid IS NULL OR c.department_id = %(department)s::uuid)
  AND (%(clinician)s::uuid IS NULL OR a.clinician_id = %(clinician)s::uuid)
  AND (%(status)s::text IS NULL OR a.status = %(status)s::text)
  AND (%(source)s::text IS NULL OR a.source = %(source)s::text)
"""

_ORDER = "ORDER BY start DESC, id"

# One statement: the count row always comes back, the page rows joined to it.
_PAGE = "".join(
    (
        "WITH listed AS (",
        _ROWS,
        "), counted AS (SELECT count(*) AS total FROM listed)\n"
        "SELECT counted.total, page.* FROM counted\n"
        "LEFT JOIN LATERAL (SELECT * FROM listed ",
        _ORDER,
        " LIMIT %(limit)s OFFSET %(offset)s) page ON true",
    )
)

_ALL = "".join(("SELECT * FROM (", _ROWS, ") listed ", _ORDER))


def _fetch(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _params(f: AdminAppointmentFilter) -> dict[str, Any]:
    return {
        "from": f.start_date,
        "to": f.end_date,
        "department": f.department_id.value if f.department_id else None,
        "clinician": f.clinician_id.value if f.clinician_id else None,
        "status": f.status.value if f.status else None,
        "source": f.source.value if f.source else None,
    }


def _row(row: dict[str, Any]) -> AdminAppointmentRow:
    return AdminAppointmentRow(
        appointment=appointment_of(row),
        patient_name=row["patient_name"],
        clinician_name=row["clinician_name"],
        department=row["department"],
        appointment_type=row["appointment_type"],
        room=row["room"],
        hospital_name=row["hospital_name"],
        time_zone=row["time_zone"],
    )


def _export(row: dict[str, Any]) -> ExportRow:
    return ExportRow(
        id=Id(row["id"]),
        start=row["start"],
        end=row["end"],
        status=AppointmentStatus(row["status"]),
        source=Source(row["source"]),
        patient_id=Id(row["patient_id"]),
        clinician_id=Id(row["clinician_id"]),
        department_id=Id(row["department_id"]),
        appointment_type_id=Id(row["appointment_type_id"]),
        room_id=Id(row["room_id"]) if row["room_id"] else None,
    )


class SqlAdminAppointments(AdminAppointments):
    """Reads booking, organisation and identity tables in one statement per call."""

    def page(
        self, appointment_filter: AdminAppointmentFilter, request: PageRequest
    ) -> Page[AdminAppointmentRow]:
        params = _params(appointment_filter) | {"limit": PAGE_SIZE, "offset": request.offset}
        rows = _fetch(_PAGE, params)
        found = tuple(_row(r) for r in rows if r["id"] is not None)
        return Page(found, rows[0]["total"], request.number)

    def all(self, appointment_filter: AdminAppointmentFilter) -> tuple[ExportRow, ...]:
        return tuple(_export(r) for r in _fetch(_ALL, _params(appointment_filter)))
