# SQL is composed from fixed fragments only; every value is a bound parameter.
import uuid
from typing import Any

from django.db import connection

from drlibre.interop.application.ports.inbound import (
    HELD,
    AppointmentFilter,
    AppointmentKind,
    AppointmentRow,
    InteropAppointmentQueries,
    Paging,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_directory import Where, page_of
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

# A booked entry is served as its appointment; an offered one shows the offered slot.
_APPOINTMENTS = """
SELECT a.id, 'appointment' AS kind, a.status, a.patient_id, a.clinician_id,
       p.user_id AS practitioner_id, a.appointment_type_id, a.room_id, a.start, a."end",
       NULL::timestamptz AS earliest, NULL::timestamptz AS latest, a.source, a.reason,
       a.cancellation_reason,
       CASE WHEN a.clinician_id = %(profile)s::uuid THEN a.clinical_notes END AS clinical_notes,
       a.start AS date, a.updated_at
FROM booking_appointmentrecord a
JOIN organisation_clinicianprofilerecord p ON p.id = a.clinician_id
UNION ALL
SELECT w.id, 'waitlist', w.status, w.patient_id, COALESCE(o.clinician_id, w.clinician_id),
       p.user_id, w.appointment_type_id, NULL, o.start, o."end", w.earliest, w.latest, NULL,
       NULL, NULL, NULL, COALESCE(o.start, w.earliest), w.updated_at
FROM booking_waitlistentryrecord w
LEFT JOIN booking_appointmentrecord o ON o.id = w.offered_appointment_id AND w.status = 'OFFERED'
LEFT JOIN organisation_clinicianprofilerecord p ON p.id = COALESCE(o.clinician_id, w.clinician_id)
WHERE w.status <> 'BOOKED'
UNION ALL
SELECT h.id, 'hold', 'HELD', NULL, h.clinician_id, p.user_id, h.appointment_type_id, NULL,
       h.start, h."end", NULL, NULL, h.source, h.reason, NULL, NULL, h.start, h.updated_at
FROM booking_bookingholdrecord h
JOIN organisation_clinicianprofilerecord p ON p.id = h.clinician_id
WHERE h.expires_at > %(now)s
"""

_EXISTS = """
SELECT EXISTS (SELECT 1 FROM booking_appointmentrecord WHERE id = %(id)s)
    OR EXISTS (SELECT 1 FROM booking_waitlistentryrecord WHERE id = %(id)s AND status <> 'BOOKED')
    OR EXISTS (SELECT 1 FROM booking_bookingholdrecord WHERE id = %(id)s AND expires_at > %(now)s)
"""

# A patient sees their appointments and entries, a clinician their agenda and its holds.
_SCOPES = {
    ReaderKind.PATIENT: "o.kind <> 'hold' AND o.patient_id = %(me)s",
    ReaderKind.CLINICIAN: "o.kind <> 'waitlist' AND o.clinician_id = %(profile)s::uuid",
    ReaderKind.ADMIN: "true",
    ReaderKind.ANONYMOUS: "false",
}


def _value(found: Id | None) -> uuid.UUID | None:
    return found.value if found else None


def _id(value: uuid.UUID | None) -> Id | None:
    return None if value is None else Id(value)


def _row(r: dict[str, Any]) -> AppointmentRow:
    kind = AppointmentKind(r["kind"])
    return AppointmentRow(
        id=Id(r["id"]),
        kind=kind,
        status=HELD if kind is AppointmentKind.HOLD else r["status"],
        patient_id=_id(r["patient_id"]),
        clinician_id=_id(r["clinician_id"]),
        practitioner_id=_id(r["practitioner_id"]),
        appointment_type_id=Id(r["appointment_type_id"]),
        room_id=_id(r["room_id"]),
        start=r["start"],
        end=r["end"],
        earliest=r["earliest"],
        latest=r["latest"],
        source=r["source"],
        reason=r["reason"],
        cancellation_reason=r["cancellation_reason"],
        clinical_notes=r["clinical_notes"],
        updated_at=r["updated_at"],
    )


class SqlInteropAppointmentQueries(InteropAppointmentQueries):
    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock

    def appointments(
        self, criteria: AppointmentFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AppointmentRow]:
        where = Where(criteria.ids)
        where.add(
            _SCOPES[reader.kind],
            me=_value(reader.user_id),
            profile=_value(reader.profile_id),
            now=self._clock.now(),
        )
        where.when(criteria.patient, "o.patient_id = %(patient)s", "patient")
        where.when(criteria.practitioner, "o.practitioner_id = %(practitioner)s", "practitioner")
        where.when(criteria.room, "o.room_id = %(room)s", "room")
        where.when(criteria.appointment_type, "o.appointment_type_id = %(kind)s", "kind")
        if criteria.statuses:
            pairs = [f"{kind}:{status}" for kind, status in criteria.statuses]
            where.add("(o.kind || ':' || o.status) = ANY(%(statuses)s)", statuses=pairs)
        where.when(criteria.start_from, "o.start >= %(start_from)s", "start_from")
        where.when(criteria.start_before, "o.start < %(start_before)s", "start_before")
        rows, total = page_of(_APPOINTMENTS, where, paging, ("date", "id"))
        return Page(tuple(_row(r) for r in rows), total, paging.page if paging else 1)

    def exists(self, appointment_id: Id) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(_EXISTS, {"id": appointment_id.value, "now": self._clock.now()})
            row = cursor.fetchone()
        return bool(row and row[0])
