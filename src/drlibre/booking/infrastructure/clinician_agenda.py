from datetime import datetime
from typing import Any

from django.db import connection

from drlibre.booking.application.ports.outbound import (
    ClinicianAgenda,
    ClinicianEntry,
    ClinicianFilter,
    ClinicianPatient,
    RoomBooking,
    RoomLabel,
    RoomsDay,
)
from drlibre.booking.infrastructure.patient_agenda import appointment_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest

_ENTRY = """
SELECT a.id, a.patient_id, a.clinician_id, a.appointment_type_id, a.room_id, a.start, a."end",
       a.status, a.source, a.reason, a.cancelled_at, a.cancellation_reason, {notes}
       u.full_name AS patient_name, u.phone AS patient_phone,
       u.birth_date AS patient_birth_date, t.name AS appointment_type, t.colour AS type_colour,
       r.name AS room
FROM booking_appointmentrecord a
JOIN identity_userrecord u ON u.id = a.patient_id
JOIN organisation_appointmenttyperecord t ON t.id = a.appointment_type_id
LEFT JOIN organisation_roomrecord r ON r.id = a.room_id
"""

_ENTRIES = (
    _ENTRY.format(notes="")
    + """
WHERE a.clinician_id = %(clinician)s
  AND (%(patient)s::uuid IS NULL OR a.patient_id = %(patient)s::uuid)
  AND (%(status)s::text IS NULL OR a.status = %(status)s::text)
  AND (%(start)s::timestamptz IS NULL OR a.start >= %(start)s::timestamptz)
  AND (%(end)s::timestamptz IS NULL OR a.start < %(end)s::timestamptz)
ORDER BY a.start
"""
)

_DETAIL = _ENTRY.format(notes="a.clinical_notes,") + "WHERE a.id = %(id)s"

_PATIENTS = """
SELECT u.id, u.full_name, u.phone,
       MAX(a.start) FILTER (WHERE a.status = 'COMPLETED' AND a.start < %(now)s) AS last_visit,
       MIN(a.start) FILTER (
           WHERE a.status IN ('BOOKED', 'CHECKED_IN') AND a.start > %(now)s
       ) AS next_visit,
       COUNT(*) OVER () AS total
FROM booking_appointmentrecord a
JOIN identity_userrecord u ON u.id = a.patient_id
WHERE a.clinician_id = %(clinician)s AND u.full_name ILIKE %(pattern)s
GROUP BY u.id, u.full_name, u.phone
ORDER BY u.full_name, u.id
LIMIT %(limit)s OFFSET %(offset)s
"""

_ROOMS = """
SELECT r.id, r.name FROM organisation_roomrecord r
JOIN organisation_clinicianprofilerecord c ON c.department_id = r.department_id
WHERE c.id = %(clinician)s AND r.active
ORDER BY r.code
"""

_ROOM_BOOKINGS = """
SELECT a.room_id, a.start, a."end",
       CASE WHEN a.clinician_id = %(clinician)s THEN u.full_name END AS patient_name
FROM booking_appointmentrecord a
JOIN organisation_roomrecord r ON r.id = a.room_id AND r.active
JOIN organisation_clinicianprofilerecord c
    ON c.id = %(clinician)s AND c.department_id = r.department_id
JOIN identity_userrecord u ON u.id = a.patient_id
WHERE a.status IN ('BOOKED', 'CHECKED_IN', 'COMPLETED')
  AND a.start < %(end)s AND a."end" > %(start)s
ORDER BY a.start, r.code
"""

_NEXT_FREE = """
SELECT MIN(s.start) AS start FROM scheduling_slot s
WHERE s.clinician_id = %(clinician)s AND s.start >= %(after)s
  AND NOT EXISTS (
      SELECT 1 FROM booking_bookingholdrecord bh
      WHERE bh.clinician_id = s.clinician_id AND bh.expires_at > %(now)s
        AND s.start < bh."end" AND s."end" > bh.start
  )
"""


def _rows(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _entry(row: dict[str, Any]) -> ClinicianEntry:
    return ClinicianEntry(
        appointment=appointment_of(row),
        patient_name=row["patient_name"],
        patient_phone=row["patient_phone"],
        patient_birth_date=row["patient_birth_date"],
        appointment_type=row["appointment_type"],
        type_colour=row["type_colour"],
        room=row["room"],
    )


def _like(search: str) -> str:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SqlClinicianAgenda(ClinicianAgenda):
    """Reads booking, organisation, identity and scheduling tables, one statement per list."""

    def entries(
        self, clinician_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        f = agenda_filter
        params = {
            "clinician": clinician_id.value,
            "patient": f.patient_id.value if f.patient_id else None,
            "status": f.status.value if f.status else None,
            "start": f.start,
            "end": f.end,
        }
        return tuple(_entry(row) for row in _rows(_ENTRIES, params))

    def detail(self, appointment_id: Id) -> ClinicianEntry | None:
        rows = _rows(_DETAIL, {"id": appointment_id.value})
        return _entry(rows[0]) if rows else None

    def patients(
        self, clinician_id: Id, request: PageRequest, now: datetime
    ) -> Page[ClinicianPatient]:
        params = {
            "clinician": clinician_id.value,
            "pattern": _like(request.search),
            "now": now,
            "limit": PAGE_SIZE,
            "offset": request.offset,
        }
        rows = _rows(_PATIENTS, params)
        items = tuple(
            ClinicianPatient(
                patient_id=Id(row["id"]),
                full_name=row["full_name"],
                phone=row["phone"],
                last_visit=row["last_visit"],
                next_visit=row["next_visit"],
            )
            for row in rows
        )
        return Page(items=items, total=rows[0]["total"] if rows else 0, number=request.number)

    def room_day(self, clinician_id: Id, start: datetime, end: datetime) -> RoomsDay:
        params = {"clinician": clinician_id.value, "start": start, "end": end}
        rooms = tuple(RoomLabel(Id(r["id"]), r["name"]) for r in _rows(_ROOMS, params))
        bookings = tuple(
            RoomBooking(Id(r["room_id"]), r["start"], r["end"], r["patient_name"])
            for r in _rows(_ROOM_BOOKINGS, params)
        )
        return RoomsDay(rooms=rooms, bookings=bookings)

    def next_free_slot(self, clinician_id: Id, after: datetime, now: datetime) -> datetime | None:
        params = {"clinician": clinician_id.value, "after": after, "now": now}
        return _rows(_NEXT_FREE, params)[0]["start"]
