from typing import Any

from django.db import connection

from drlibre.booking.application.ports.inbound import (
    BookingOption,
    BookingOptionQueries,
    BookingOptions,
)
from drlibre.shared_kernel.ids import Id

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


def _options(sql: str, params: dict[str, Any]) -> tuple[BookingOption, ...]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return tuple(BookingOption(Id(i), label) for i, label in cursor.fetchall())


class SqlBookingOptionQueries(BookingOptionQueries):
    """Reads organisation and identity tables in one statement per list."""

    def type_options(self, *, online_only: bool) -> tuple[BookingOption, ...]:
        return _options(_TYPES, {"online_only": online_only})

    def clinician_options(self) -> tuple[BookingOption, ...]:
        return _options(_CLINICIANS, {})

    def booking_options(self, appointment_type_id: Id) -> BookingOptions:
        with connection.cursor() as cursor:
            cursor.execute(_BOOKING_OPTIONS, {"type": appointment_type_id.value})
            rows = cursor.fetchall()
        clinicians, rooms = (
            tuple(BookingOption(Id(i), label) for k, i, label in rows if k == kind)
            for kind in (0, 1)
        )
        return BookingOptions(clinicians, rooms)
