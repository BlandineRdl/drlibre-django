from datetime import datetime
from typing import Any

from django.db import connection

from drlibre.reporting.application.ports.outbound import ActivityQueries
from drlibre.reporting.domain.available_minutes import Absence, ClinicianSchedule, RuleHours
from drlibre.reporting.domain.dashboard import BusyClinician, DayCount, Range, Tally
from drlibre.shared_kernel.ids import Id

# Appointments of the range, each with its local day in its clinician's hospital zone.
_IN_RANGE = """
WITH located AS (
    SELECT a.clinician_id, a.start, a."end", a.status, a.source,
           u.active AND u.role = 'CLINICIAN' AS clinician_active,
           (a.start AT TIME ZONE h.time_zone)::date AS day,
           (%(now)s::timestamptz AT TIME ZONE h.time_zone)::date AS today
    FROM booking_appointmentrecord a
    JOIN organisation_clinicianprofilerecord c ON c.id = a.clinician_id
    JOIN identity_userrecord u ON u.id = c.user_id
    JOIN organisation_departmentrecord d ON d.id = c.department_id
    JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
    WHERE a.start >= %(earliest)s AND a.start < %(latest)s
), in_range AS (
    SELECT * FROM located WHERE day > today - %(length)s AND day <= today
)
"""

_TALLY = "".join(
    (
        _IN_RANGE,
        """
SELECT COUNT(*) FILTER (WHERE status <> 'CANCELLED') AS appointments,
       COUNT(*) FILTER (WHERE status = 'CANCELLED') AS cancellations,
       COUNT(*) FILTER (WHERE status = 'NO_SHOW') AS no_shows,
       COUNT(*) FILTER (
           WHERE status <> 'CANCELLED' AND source IN ('ONLINE', 'ROUND_ROBIN')
       ) AS online,
       COALESCE(FLOOR(SUM(EXTRACT(EPOCH FROM "end" - start)) FILTER (
           WHERE status NOT IN ('CANCELLED', 'NO_SHOW') AND clinician_active
       ) / 60), 0)::int AS active_minutes
FROM in_range
""",
    )
)

_PER_DAY = "".join(
    (
        _IN_RANGE,
        """
SELECT day, COUNT(*) AS count FROM in_range
WHERE status <> 'CANCELLED'
GROUP BY day ORDER BY day
""",
    )
)

_BUSIEST = "".join(
    (
        _IN_RANGE,
        """
SELECT r.clinician_id, u.full_name, COUNT(*) AS count
FROM in_range r
JOIN organisation_clinicianprofilerecord c ON c.id = r.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id
WHERE r.status <> 'CANCELLED'
GROUP BY r.clinician_id, u.full_name
ORDER BY count DESC, u.full_name, r.clinician_id
LIMIT %(limit)s
""",
    )
)

_WAITLIST = """
SELECT COUNT(*) AS size FROM booking_waitlistentryrecord WHERE status IN ('WAITING', 'OFFERED')
"""

_ACTIVE = """
SELECT c.id, h.time_zone
FROM organisation_clinicianprofilerecord c
JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
JOIN organisation_departmentrecord d ON d.id = c.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
"""

_RULES = """
SELECT r.clinician_id, r.weekday, r.start, r."end", r.valid_from, r.valid_to
FROM scheduling_availabilityrulemodel r
JOIN organisation_clinicianprofilerecord c ON c.id = r.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
"""

_TIME_OFF = """
SELECT t.clinician_id, t.start, t."end"
FROM scheduling_timeoffmodel t
JOIN organisation_clinicianprofilerecord c ON c.id = t.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
WHERE t.start < %(end)s AND t."end" > %(start)s
"""


def _rows(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _range(now: datetime, period: Range) -> dict[str, Any]:
    earliest, latest = period.window(now)
    return {"now": now, "earliest": earliest, "latest": latest, "length": period.length}


class SqlActivityQueries(ActivityQueries):
    """Reads booking, organisation, identity and scheduling tables, one statement per figure."""

    def tally(self, now: datetime, period: Range) -> Tally:
        (row,) = _rows(_TALLY, _range(now, period))
        return Tally(**row)

    def per_day(self, now: datetime, period: Range) -> tuple[DayCount, ...]:
        rows = _rows(_PER_DAY, _range(now, period))
        return tuple(DayCount(row["day"], row["count"]) for row in rows)

    def busiest(self, now: datetime, period: Range, limit: int) -> tuple[BusyClinician, ...]:
        rows = _rows(_BUSIEST, {**_range(now, period), "limit": limit})
        return tuple(
            BusyClinician(Id(row["clinician_id"]), row["full_name"], row["count"]) for row in rows
        )

    def waitlist_size(self) -> int:
        (row,) = _rows(_WAITLIST, {})
        return row["size"]

    def schedules(self, start: datetime, end: datetime) -> tuple[ClinicianSchedule, ...]:
        rules: dict[Any, list[RuleHours]] = {}
        for row in _rows(_RULES, {}):
            rules.setdefault(row["clinician_id"], []).append(
                RuleHours(
                    row["weekday"], row["start"], row["end"], row["valid_from"], row["valid_to"]
                )
            )
        absences: dict[Any, list[Absence]] = {}
        for row in _rows(_TIME_OFF, {"start": start, "end": end}):
            absences.setdefault(row["clinician_id"], []).append(Absence(row["start"], row["end"]))
        return tuple(
            ClinicianSchedule(
                time_zone=row["time_zone"],
                rules=tuple(rules.get(row["id"], ())),
                absences=tuple(absences.get(row["id"], ())),
            )
            for row in _rows(_ACTIVE, {})
        )
