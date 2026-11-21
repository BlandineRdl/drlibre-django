from typing import Any

from django.db import connection

from drlibre.booking.application.ports.outbound import AgendaEntry, AgendaFilter, PatientAgenda
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.shared_kernel.ids import Id

_SQL = """
SELECT a.id, a.patient_id, a.clinician_id, a.appointment_type_id, a.room_id, a.start, a."end",
       a.status, a.source, a.reason, a.cancelled_at, a.cancellation_reason,
       u.full_name AS clinician_name, c.title AS clinician_title, sp.name AS specialty,
       h.name AS hospital_name, h.street, h.postal_code, h.city, h.time_zone,
       d.name AS department, r.name AS room, t.name AS appointment_type,
       t.bookable_online
FROM booking_appointmentrecord a
JOIN organisation_clinicianprofilerecord c ON c.id = a.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id
JOIN organisation_specialtyrecord sp ON sp.id = c.specialty_id
JOIN organisation_departmentrecord d ON d.id = c.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
JOIN organisation_appointmenttyperecord t ON t.id = a.appointment_type_id
LEFT JOIN organisation_roomrecord r ON r.id = a.room_id
WHERE a.patient_id = %(patient)s
  AND (%(clinician)s::uuid IS NULL OR a.clinician_id = %(clinician)s::uuid)
  AND (%(status)s::text IS NULL OR a.status = %(status)s::text)
  AND (%(start)s::timestamptz IS NULL OR a.start >= %(start)s::timestamptz)
  AND (%(end)s::timestamptz IS NULL OR a.start < %(end)s::timestamptz)
ORDER BY a.start
"""


def appointment_of(row: dict[str, Any]) -> Appointment:
    """The appointment of a row selecting the appointment columns, notes when selected."""
    return Appointment(
        id=Id(row["id"]),
        patient_id=Id(row["patient_id"]),
        clinician_id=Id(row["clinician_id"]),
        appointment_type_id=Id(row["appointment_type_id"]),
        room_id=Id(row["room_id"]) if row["room_id"] else None,
        start=row["start"],
        end=row["end"],
        status=AppointmentStatus(row["status"]),
        source=Source(row["source"]),
        reason=row["reason"],
        cancelled_at=row["cancelled_at"],
        cancellation_reason=row["cancellation_reason"],
        clinical_notes=row.get("clinical_notes"),
    )


def _entry(row: dict[str, Any]) -> AgendaEntry:
    return AgendaEntry(
        appointment=appointment_of(row),
        clinician_name=row["clinician_name"],
        clinician_title=row["clinician_title"],
        specialty=row["specialty"],
        hospital_name=row["hospital_name"],
        hospital_address=f"{row['street']}, {row['postal_code']} {row['city']}",
        time_zone=row["time_zone"],
        department=row["department"],
        room=row["room"],
        appointment_type=row["appointment_type"],
        bookable_online=row["bookable_online"],
    )


class SqlPatientAgenda(PatientAgenda):
    """Reads booking, organisation and identity tables in one statement, like search."""

    def entries(self, patient_id: Id, agenda_filter: AgendaFilter) -> tuple[AgendaEntry, ...]:
        params = {
            "patient": patient_id.value,
            "clinician": agenda_filter.clinician_id.value if agenda_filter.clinician_id else None,
            "status": agenda_filter.status.value if agenda_filter.status else None,
            "start": agenda_filter.start,
            "end": agenda_filter.end,
        }
        with connection.cursor() as cursor:
            cursor.execute(_SQL, params)
            names = [column.name for column in cursor.description or ()]
            return tuple(_entry(dict(zip(names, row, strict=True))) for row in cursor.fetchall())
