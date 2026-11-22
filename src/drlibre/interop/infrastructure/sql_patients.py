# SQL is composed from fixed fragments only; every value is a bound parameter.
from django.db import connection

from drlibre.interop.application.ports.inbound import (
    Paging,
    PatientFilter,
    PatientQueries,
    PatientRow,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_directory import Where, like, page_of
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

_PATIENTS = """
SELECT u.id, u.full_name AS name, u.email, u.phone, u.birth_date, u.active, u.updated_at
FROM identity_userrecord u
WHERE u.role = 'PATIENT'
"""

# A clinician's own patients are those with at least one appointment, as on their patients page.
_OWN = """
EXISTS (SELECT 1 FROM booking_appointmentrecord a
        WHERE a.patient_id = o.id AND a.clinician_id = %(profile)s)
"""


def _value(found: Id | None) -> object:
    return found.value if found else None


class SqlPatientQueries(PatientQueries):
    def patients(
        self, criteria: PatientFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PatientRow]:
        where = Where(criteria.ids)
        if reader.kind is ReaderKind.PATIENT:
            where.add("o.id = %(me)s", me=_value(reader.user_id))
        elif reader.kind is ReaderKind.CLINICIAN:
            where.add(_OWN, profile=_value(reader.profile_id))
        elif not reader.is_admin:
            where.add("false")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(criteria.email, "lower(o.email) = lower(%(email)s)", "email")
        where.when(criteria.phone, "o.phone = %(phone)s", "phone")
        where.when(criteria.birth_date, "o.birth_date = %(born)s", "born")
        rows, total = page_of(_PATIENTS, where, paging, ("name", "id"))
        items = tuple(
            PatientRow(
                id=Id(r["id"]),
                full_name=r["name"],
                email=r["email"],
                phone=r["phone"],
                birth_date=r["birth_date"],
                active=r["active"],
                updated_at=r["updated_at"],
            )
            for r in rows
        )
        return Page(items, total, paging.page if paging else 1)

    def exists(self, patient_id: Id) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM identity_userrecord"
                " WHERE id = %s AND role = 'PATIENT')",
                [patient_id.value],
            )
            row = cursor.fetchone()
        return bool(row and row[0])
