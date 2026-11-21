# ruff: noqa: S608  # SQL is composed from fixed fragments only; every value is a bound parameter.
from typing import Any

from django.db import connection

from drlibre.booking.application.ports.inbound import (
    BookingOptions,
    WaitlistEntry,
    WaitlistOption,
    WaitlistQueries,
    WaitlistRow,
    WaitlistStatus,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest

_ROWS = """
SELECT w.id, w.patient_id, w.appointment_type_id, w.clinician_id, w.earliest, w.latest,
       w.status, w.created_at, w.offered_appointment_id,
       u.full_name AS patient_name, t.name AS appointment_type, h.name AS hospital_name,
       h.time_zone, cu.full_name AS clinician_name, oa.start AS offered_start
FROM booking_waitlistentryrecord w
JOIN identity_userrecord u ON u.id = w.patient_id
JOIN organisation_appointmenttyperecord t ON t.id = w.appointment_type_id
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
LEFT JOIN organisation_clinicianprofilerecord c ON c.id = w.clinician_id
LEFT JOIN identity_userrecord cu ON cu.id = c.user_id
LEFT JOIN booking_appointmentrecord oa ON oa.id = w.offered_appointment_id
"""

_OWN = _ROWS + "WHERE w.patient_id = %(patient)s ORDER BY w.created_at DESC, w.id DESC"

# One statement: the count row always comes back, the page rows joined to it.
_PAGE = f"""
WITH listed AS ({_ROWS} WHERE (%(status)s::text IS NULL OR w.status = %(status)s::text)),
     counted AS (SELECT count(*) AS total FROM listed)
SELECT counted.total, page.*
FROM counted
LEFT JOIN LATERAL (
    SELECT * FROM listed ORDER BY created_at, id LIMIT %(limit)s OFFSET %(offset)s
) page ON true
"""

_TYPES = """
SELECT t.id, t.name || ' · ' || h.name AS label
FROM organisation_appointmenttyperecord t
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
WHERE t.active AND h.active AND (NOT %(online_only)s OR t.bookable_online)
ORDER BY label, t.id
"""

_CLINICIANS = """
SELECT c.id, u.full_name || ' · ' || d.name AS label
FROM organisation_clinicianprofilerecord c
JOIN identity_userrecord u ON u.id = c.user_id
JOIN organisation_departmentrecord d ON d.id = c.department_id
WHERE u.active AND u.role = 'CLINICIAN'
ORDER BY label, c.id
"""

# Clinicians then rooms of the type's department, in one statement.
_BOOKING_OPTIONS = """
SELECT 0 AS kind, c.id, u.full_name || ' · ' || d.name AS label
FROM organisation_appointmenttyperecord t
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_clinicianprofilerecord c ON c.department_id = d.id
JOIN identity_userrecord u ON u.id = c.user_id
WHERE t.id = %(type)s AND u.active AND u.role = 'CLINICIAN'
UNION ALL
SELECT 1, r.id, r.name || ' (' || r.code || ')'
FROM organisation_appointmenttyperecord t
JOIN organisation_roomrecord r ON r.department_id = t.department_id
WHERE t.id = %(type)s AND r.active
ORDER BY kind, label, id
"""


def _fetch(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _row(row: dict[str, Any]) -> WaitlistRow:
    entry = WaitlistEntry(
        id=Id(row["id"]),
        patient_id=Id(row["patient_id"]),
        appointment_type_id=Id(row["appointment_type_id"]),
        clinician_id=Id(row["clinician_id"]) if row["clinician_id"] else None,
        earliest=row["earliest"],
        latest=row["latest"],
        status=WaitlistStatus(row["status"]),
        created_at=row["created_at"],
        offered_appointment_id=(
            Id(row["offered_appointment_id"]) if row["offered_appointment_id"] else None
        ),
    )
    return WaitlistRow(
        entry=entry,
        patient_name=row["patient_name"],
        appointment_type=row["appointment_type"],
        hospital_name=row["hospital_name"],
        time_zone=row["time_zone"],
        clinician_name=row["clinician_name"],
        offered_start=row["offered_start"],
    )


def _options(sql: str, params: dict[str, Any]) -> tuple[WaitlistOption, ...]:
    return tuple(WaitlistOption(Id(r["id"]), r["label"]) for r in _fetch(sql, params))


class SqlWaitlistQueries(WaitlistQueries):
    """Reads booking, organisation and identity tables in one statement per call."""

    def own_entries(self, patient_id: Id) -> tuple[WaitlistRow, ...]:
        return tuple(_row(r) for r in _fetch(_OWN, {"patient": patient_id.value}))

    def page(self, status: str, request: PageRequest) -> Page[WaitlistRow]:
        known = status if status in set(WaitlistStatus) else None
        params = {"status": known, "limit": PAGE_SIZE, "offset": request.offset}
        rows = _fetch(_PAGE, params)
        found = tuple(_row(r) for r in rows if r["id"] is not None)
        return Page(found, rows[0]["total"], request.number)

    def type_options(self, *, online_only: bool) -> tuple[WaitlistOption, ...]:
        return _options(_TYPES, {"online_only": online_only})

    def clinician_options(self) -> tuple[WaitlistOption, ...]:
        return _options(_CLINICIANS, {})

    def booking_options(self, appointment_type_id: Id) -> BookingOptions:
        rows = _fetch(_BOOKING_OPTIONS, {"type": appointment_type_id.value})
        clinicians, rooms = (
            tuple(WaitlistOption(Id(r["id"]), r["label"]) for r in rows if r["kind"] == kind)
            for kind in (0, 1)
        )
        return BookingOptions(clinicians, rooms)
