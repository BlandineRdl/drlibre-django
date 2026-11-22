from datetime import datetime
from typing import Any

from django.db import connection

from drlibre.reporting.application.ports.outbound import ActivityQueries
from drlibre.reporting.domain.available_minutes import Absence, ClinicianSchedule, RuleHours
from drlibre.reporting.domain.dashboard import Activity, BusyClinician, DayCount, Range, Tally
from drlibre.shared_kernel.ids import Id

# One read of the range: each clinician's zone and today first, so each row converts once.
_ACTIVITY = """
WITH staff AS MATERIALIZED (
    SELECT c.id, u.full_name, u.active AND u.role = 'CLINICIAN' AS clinician_active,
           h.time_zone, (%(now)s::timestamptz AT TIME ZONE h.time_zone)::date AS today
    FROM organisation_clinicianprofilerecord c
    JOIN identity_userrecord u ON u.id = c.user_id
    JOIN organisation_departmentrecord d ON d.id = c.department_id
    JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
), located AS MATERIALIZED (
    SELECT a.clinician_id, a.start, a."end", a.status, a.source, s.full_name,
           s.clinician_active, s.today, (a.start AT TIME ZONE s.time_zone)::date AS day
    FROM booking_appointmentrecord a
    JOIN staff s ON s.id = a.clinician_id
    WHERE a.start >= %(earliest)s AND a.start < %(latest)s
), in_range AS MATERIALIZED (
    SELECT * FROM located WHERE day > today - %(length)s AND day <= today
), per_day AS (
    SELECT day, COUNT(*) AS count FROM in_range WHERE status <> 'CANCELLED' GROUP BY day
), busiest AS (
    SELECT clinician_id, full_name, COUNT(*) AS count FROM in_range
    WHERE status <> 'CANCELLED'
    GROUP BY clinician_id, full_name
    ORDER BY count DESC, full_name, clinician_id
    LIMIT %(limit)s
)
SELECT COUNT(*) FILTER (WHERE status <> 'CANCELLED') AS appointments,
       COUNT(*) FILTER (WHERE status = 'CANCELLED') AS cancellations,
       COUNT(*) FILTER (WHERE status = 'NO_SHOW') AS no_shows,
       COUNT(*) FILTER (
           WHERE status <> 'CANCELLED' AND source IN ('ONLINE', 'ROUND_ROBIN')
       ) AS online,
       COALESCE(FLOOR(SUM(EXTRACT(EPOCH FROM "end" - start)) FILTER (
           WHERE status NOT IN ('CANCELLED', 'NO_SHOW') AND clinician_active
       ) / 60), 0)::int AS active_minutes,
       (SELECT array_agg(day ORDER BY day) FROM per_day) AS days,
       (SELECT array_agg(count ORDER BY day) FROM per_day) AS day_counts,
       (SELECT array_agg(clinician_id ORDER BY count DESC, full_name, clinician_id)
        FROM busiest) AS busy_ids,
       (SELECT array_agg(full_name ORDER BY count DESC, full_name, clinician_id)
        FROM busiest) AS busy_names,
       (SELECT array_agg(count ORDER BY count DESC, full_name, clinician_id)
        FROM busiest) AS busy_counts
FROM in_range
"""

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
    """Reads booking, organisation, identity and scheduling tables."""

    def activity(self, now: datetime, period: Range, limit: int) -> Activity:
        (row,) = _rows(_ACTIVITY, {**_range(now, period), "limit": limit})
        figures = ("appointments", "cancellations", "no_shows", "online", "active_minutes")
        days = zip(row["days"] or (), row["day_counts"] or (), strict=True)
        busy = zip(
            row["busy_ids"] or (), row["busy_names"] or (), row["busy_counts"] or (), strict=True
        )
        return Activity(
            tally=Tally(*(row[name] for name in figures)),
            per_day=tuple(DayCount(day, count) for day, count in days),
            busiest=tuple(BusyClinician(Id(i), name, count) for i, name, count in busy),
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
