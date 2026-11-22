# ruff: noqa: S608  # SQL is composed from fixed fragments only; every value is a bound parameter.
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from django.db import connection

from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.criteria import Moment, SearchCriteria, Sort, Window
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import (
    BookableType,
    FilterOptions,
    FirstSlot,
    Found,
    HospitalDetail,
    HospitalResult,
    NextSlots,
    Option,
    ProviderDetail,
    ProviderResult,
    SpecialtyDetail,
    SpecialtyResult,
    TypeFirstSlot,
)
from drlibre.shared_kernel.ids import Id

type Params = dict[str, Any]

# Bookable providers: active clinician, specialty and hospital, plus the type their times are for.
_PROVIDERS = """
SELECT c.id AS clinician_id, u.full_name, c.title,
       sp.id AS specialty_id, sp.name AS specialty_name,
       h.id AS hospital_id, h.name AS hospital_name, h.street, h.postal_code, h.city,
       h.time_zone, h.latitude, h.longitude,
       d.id AS department_id, d.name AS department_name,
       ty.id AS type_id, ty.name AS type_name, ty.duration_minutes, ty.buffer_minutes,
       ty.needs_room
FROM organisation_clinicianprofilerecord c
JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
JOIN organisation_specialtyrecord sp ON sp.id = c.specialty_id AND sp.active
JOIN organisation_departmentrecord d ON d.id = c.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id AND h.active
JOIN LATERAL (
    SELECT t.* FROM organisation_appointmenttyperecord t
    WHERE t.department_id = d.id AND t.active AND t.bookable_online {type_filter}
    ORDER BY t.duration_minutes, t.name, t.id LIMIT 1
) ty ON true
WHERE {conditions}
"""

_NOT_HELD = """
NOT EXISTS (
    SELECT 1 FROM booking_bookingholdrecord bh
    WHERE bh.clinician_id = s.clinician_id AND bh.expires_at > %(now)s
      AND s.start < bh."end" + make_interval(mins => {buffer}) AND s."end" > bh.start
)
"""

# Like placement, a type with a room needs one active room of its department free all along.
# The range overlap form lets PostgreSQL use the `appointment_room_period` index.
_ROOM_FREE = """
(NOT {kind}.needs_room OR EXISTS (
    SELECT 1 FROM organisation_roomrecord r
    WHERE r.department_id = {department} AND r.active
      AND NOT EXISTS (
          SELECT 1 FROM booking_appointmentrecord a
          WHERE a.room_id = r.id AND a.status NOT IN ('CANCELLED', 'NO_SHOW')
            AND tstzrange(a.start, a."end", '[)') && tstzrange(s.start, s."end", '[)')
      )
))
"""

_MOMENTS = {
    Moment.MORNING: "(s.start AT TIME ZONE p.time_zone)::time < time '12:00'",
    Moment.AFTERNOON: "(s.start AT TIME ZONE p.time_zone)::time >= time '12:00'"
    " AND (s.start AT TIME ZONE p.time_zone)::time < time '17:00'",
    Moment.EVENING: "(s.start AT TIME ZONE p.time_zone)::time >= time '17:00'",
}
_WINDOWS = {
    Window.TODAY: "(s.start AT TIME ZONE p.time_zone)::date"
    " <= (%(now)s::timestamptz AT TIME ZONE p.time_zone)::date",
    Window.DAYS_3: "s.start < %(now)s::timestamptz + interval '3 days'",
    Window.DAYS_7: "s.start < %(now)s::timestamptz + interval '7 days'",
}
_DISTANCE = """
CASE WHEN p.latitude IS NULL OR p.longitude IS NULL THEN NULL ELSE
    2 * 6371 * asin(least(1, sqrt(
        power(sin(radians(p.latitude - %(lat)s::float8) / 2), 2)
        + cos(radians(%(lat)s::float8)) * cos(radians(p.latitude))
          * power(sin(radians(p.longitude - %(lon)s::float8) / 2), 2))))
END
"""


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _rows(sql: str, params: Params) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


class SqlSearchQueries(SearchQueries):
    """Reads the organisation, identity, scheduling and booking tables, one statement per list."""

    def providers(self, criteria: SearchCriteria, horizon: Horizon) -> Found[ProviderResult]:
        base, params = _base(criteria, horizon)
        # Rank on the first slot alone, page, then read the next slots of the kept rows only.
        sql = (  # nosec B608
            f"""
WITH prov AS ({base}),
firsts AS ({_firsts(criteria)}),
page AS (
    SELECT r.*, COUNT(*) OVER () AS total FROM firsts r
    ORDER BY {_order(criteria, "r.first_start", "r.full_name", "r.clinician_id", "r.distance_km")}
    LIMIT %(limit)s OFFSET %(offset)s
)
SELECT p.*, n.starts FROM page p
LEFT JOIN LATERAL ({_slots(criteria, limit=3)}) n ON true
ORDER BY {_order(criteria, "p.first_start", "p.full_name", "p.clinician_id", "p.distance_km")}
"""
        )
        rows = _rows(sql, params | _paging(criteria))
        return Found(tuple(_provider(r) for r in rows), int(rows[0]["total"]) if rows else 0)

    def hospitals(self, criteria: SearchCriteria, horizon: Horizon) -> Found[HospitalResult]:
        base, params = _base(criteria, horizon)
        sql = (  # nosec B608
            f"""
WITH prov AS ({base}),
firsts AS ({_firsts(criteria)}),
hosp AS (
    SELECT hospital_id, hospital_name, street, postal_code, city, time_zone, distance_km,
           COUNT(*) AS providers, COUNT(first_start) AS with_slots, MIN(first_start) AS first_start,
           (array_agg(type_id ORDER BY first_start NULLS LAST, clinician_id))[1] AS type_id,
           (array_agg(type_name ORDER BY first_start NULLS LAST, clinician_id))[1] AS type_name,
           (array_agg(department_id ORDER BY first_start NULLS LAST, clinician_id))[1]
               AS department_id,
           array_agg(DISTINCT specialty_name ORDER BY specialty_name) AS specialties
    FROM firsts
    GROUP BY hospital_id, hospital_name, street, postal_code, city, time_zone, distance_km
)
SELECT r.*, COUNT(*) OVER () AS total FROM hosp r
ORDER BY {_order(criteria, "r.first_start", "r.hospital_name", "r.hospital_id", "r.distance_km")}
LIMIT %(limit)s OFFSET %(offset)s
"""
        )
        rows = _rows(sql, params | _paging(criteria))
        return Found(tuple(_hospital(r) for r in rows), int(rows[0]["total"]) if rows else 0)

    def specialties(self, criteria: SearchCriteria, horizon: Horizon) -> Found[SpecialtyResult]:
        base, params = _base(criteria, horizon)
        sql = (  # nosec B608
            f"""
WITH prov AS ({base}),
firsts AS ({_firsts(criteria)}),
spec AS (
    SELECT specialty_id, specialty_name,
           COUNT(*) AS providers, COUNT(DISTINCT hospital_id) AS hospitals,
           MIN(first_start) AS first_start, MIN(distance_km) AS distance_km,
           (array_agg(type_id ORDER BY first_start NULLS LAST, clinician_id))[1] AS type_id,
           (array_agg(type_name ORDER BY first_start NULLS LAST, clinician_id))[1] AS type_name,
           (array_agg(department_id ORDER BY first_start NULLS LAST, clinician_id))[1]
               AS department_id,
           (array_agg(time_zone ORDER BY first_start NULLS LAST, clinician_id))[1] AS time_zone
    FROM firsts
    GROUP BY specialty_id, specialty_name
)
SELECT r.*, COUNT(*) OVER () AS total FROM spec r
ORDER BY {_order(criteria, "r.first_start", "r.specialty_name", "r.specialty_id", "r.distance_km")}
LIMIT %(limit)s OFFSET %(offset)s
"""
        )
        rows = _rows(sql, params | _paging(criteria))
        return Found(tuple(_specialty(r) for r in rows), int(rows[0]["total"]) if rows else 0)

    def provider(self, provider_id: Id) -> ProviderDetail | None:
        sql = (
            "SELECT p.*, c.bio FROM ("  # nosec B608
            + _PROVIDERS.format(type_filter="", conditions="c.id = %(id)s")
            + ") p JOIN organisation_clinicianprofilerecord c ON c.id = p.clinician_id"
        )
        rows = _rows(sql, {"id": provider_id.value})
        if not rows:
            return None
        row = rows[0]
        types = _rows(
            """
SELECT id, name, duration_minutes FROM organisation_appointmenttyperecord
WHERE department_id = %(department)s AND active AND bookable_online
ORDER BY duration_minutes, name, id
""",
            {"department": row["department_id"]},
        )
        return ProviderDetail(
            id=Id(row["clinician_id"]),
            full_name=row["full_name"],
            title=row["title"],
            specialty_name=row["specialty_name"],
            bio=row["bio"],
            hospital_id=Id(row["hospital_id"]),
            hospital_name=row["hospital_name"],
            department_id=Id(row["department_id"]),
            department_name=row["department_name"],
            city=row["city"],
            time_zone=row["time_zone"],
            types=tuple(BookableType(Id(t["id"]), t["name"], t["duration_minutes"]) for t in types),
        )

    def hospital(self, hospital_id: Id) -> HospitalDetail | None:
        rows = _rows(
            """
SELECT id, name, street, postal_code, city, country, phone, description, time_zone
FROM organisation_hospitalrecord WHERE id = %(id)s AND active
""",
            {"id": hospital_id.value},
        )
        if not rows:
            return None
        row = rows[0]
        offer = _rows(
            "SELECT DISTINCT department_name, specialty_name FROM ("  # nosec B608
            + _PROVIDERS.format(type_filter="", conditions="h.id = %(id)s")
            + ") p ORDER BY department_name, specialty_name",
            {"id": hospital_id.value},
        )
        return HospitalDetail(
            id=Id(row["id"]),
            name=row["name"],
            street=row["street"],
            postal_code=row["postal_code"],
            city=row["city"],
            country=row["country"],
            phone=row["phone"],
            description=row["description"],
            time_zone=row["time_zone"],
            departments=tuple(dict.fromkeys(o["department_name"] for o in offer)),
            specialties=tuple(sorted({o["specialty_name"] for o in offer})),
        )

    def specialty(self, specialty_id: Id) -> SpecialtyDetail | None:
        rows = _rows(
            "SELECT id, name FROM organisation_specialtyrecord WHERE id = %(id)s AND active",
            {"id": specialty_id.value},
        )
        return SpecialtyDetail(Id(rows[0]["id"]), rows[0]["name"]) if rows else None

    def filter_options(self) -> FilterOptions:
        specialties = _rows(
            "SELECT id, name AS label FROM organisation_specialtyrecord WHERE active"
            " ORDER BY lower(name), id",
            {},
        )
        hospitals = _rows(
            "SELECT id, name AS label FROM organisation_hospitalrecord WHERE active"
            " ORDER BY lower(name), id",
            {},
        )
        types = _rows(
            """
SELECT t.id, t.name || ' (' || d.name || ', ' || h.name || ')' AS label
FROM organisation_appointmenttyperecord t
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id AND h.active
WHERE t.active AND t.bookable_online
ORDER BY lower(t.name), h.name, d.name, t.id
""",
            {},
        )

        def options(rows: list[dict[str, Any]]) -> tuple[Option, ...]:
            return tuple(Option(Id(r["id"]), r["label"]) for r in rows)

        return FilterOptions(options(specialties), options(hospitals), options(types))

    def free_starts(
        self, provider_id: Id, type_id: Id, horizon: Horizon, start: datetime, end: datetime
    ) -> tuple[datetime, ...]:
        sql = (  # nosec B608
            f"""
SELECT s.start FROM scheduling_slot s
JOIN organisation_clinicianprofilerecord c ON c.id = s.clinician_id
JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
JOIN organisation_appointmenttyperecord t
    ON t.id = s.appointment_type_id AND t.active AND t.bookable_online
   AND t.department_id = c.department_id
WHERE s.clinician_id = %(clinician)s AND s.appointment_type_id = %(type)s
  AND s.start >= greatest(%(start)s::timestamptz, %(from)s::timestamptz)
  AND s."end" <= least(%(end)s::timestamptz, %(to)s::timestamptz)
  AND {_NOT_HELD.format(buffer="t.buffer_minutes")}
  AND {_ROOM_FREE.format(kind="t", department="t.department_id")}
ORDER BY s.start
"""
        )
        params = {
            "clinician": provider_id.value,
            "type": type_id.value,
            "start": start,
            "end": end,
            "from": horizon.start,
            "to": horizon.end,
            "now": horizon.now,
        }
        return tuple(row["start"] for row in _rows(sql, params))

    def first_by_type(self, hospital_id: Id, horizon: Horizon) -> tuple[TypeFirstSlot, ...]:
        sql = (  # nosec B608
            f"""
SELECT t.id, t.name, t.duration_minutes, d.id AS department_id, d.name AS department_name,
       (SELECT MIN(s.start) FROM scheduling_slot s
        JOIN organisation_clinicianprofilerecord c ON c.id = s.clinician_id
        JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
        WHERE s.appointment_type_id = t.id AND c.department_id = d.id
          AND s.start >= %(from)s AND s."end" <= %(to)s
          AND {_NOT_HELD.format(buffer="t.buffer_minutes")}
          AND {_ROOM_FREE.format(kind="t", department="d.id")}) AS start
FROM organisation_appointmenttyperecord t
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id AND h.active
WHERE h.id = %(hospital)s AND t.active AND t.bookable_online
  AND EXISTS (
      SELECT 1 FROM organisation_clinicianprofilerecord c
      JOIN identity_userrecord u ON u.id = c.user_id AND u.active AND u.role = 'CLINICIAN'
      JOIN organisation_specialtyrecord sp ON sp.id = c.specialty_id AND sp.active
      WHERE c.department_id = d.id)
ORDER BY d.name, t.duration_minutes, t.name, t.id
"""
        )
        params = {
            "hospital": hospital_id.value,
            "from": horizon.start,
            "to": horizon.end,
            "now": horizon.now,
        }
        return tuple(
            TypeFirstSlot(
                type_id=Id(r["id"]),
                type_name=r["name"],
                duration_minutes=r["duration_minutes"],
                department_id=Id(r["department_id"]),
                department_name=r["department_name"],
                start=r["start"],
            )
            for r in _rows(sql, params)
        )


def _base(criteria: SearchCriteria, horizon: Horizon) -> tuple[str, Params]:
    """The bookable providers matching the text and static filters, with the query parameters."""
    params: Params = {"now": horizon.now, "from": horizon.start, "to": horizon.end}
    conditions = ["true"]
    if criteria.text:
        params["text"] = _like(criteria.text)
        conditions.append(
            """(h.name ILIKE %(text)s OR h.city ILIKE %(text)s OR u.full_name ILIKE %(text)s
 OR sp.name ILIKE %(text)s OR d.name ILIKE %(text)s
 OR EXISTS (SELECT 1 FROM organisation_appointmenttyperecord t2
            WHERE t2.department_id = d.id AND t2.active AND t2.bookable_online
              AND t2.name ILIKE %(text)s))"""
        )
    if criteria.specialty:
        params["specialty"] = criteria.specialty.value
        conditions.append("c.specialty_id = %(specialty)s")
    if criteria.hospital:
        params["hospital"] = criteria.hospital.value
        conditions.append("h.id = %(hospital)s")
    if criteria.city:
        params["city"] = _like(criteria.city)
        conditions.append("h.city ILIKE %(city)s")
    type_filter = ""
    if criteria.appointment_type:
        params["type"] = criteria.appointment_type.value
        type_filter = "AND t.id = %(type)s"
    if criteria.from_date:
        params["from_date"] = criteria.from_date
    if criteria.location:
        params["lat"], params["lon"] = criteria.location.latitude, criteria.location.longitude
    sql = _PROVIDERS.format(type_filter=type_filter, conditions=" AND ".join(conditions))
    return sql, params


def _slots(criteria: SearchCriteria, *, limit: int) -> str:
    """The provider's first free starts that pass the time filters, as one array column."""
    filters = [
        "s.start >= %(from)s",
        "s.start < %(to)s",
        _NOT_HELD.format(buffer="p.buffer_minutes"),
        _ROOM_FREE.format(kind="p", department="p.department_id"),
    ]
    if criteria.from_date:
        filters.append("(s.start AT TIME ZONE p.time_zone)::date >= %(from_date)s")
    if criteria.window is not Window.ANY:
        filters.append(_WINDOWS[criteria.window])
    if criteria.moment is not Moment.ANY:
        filters.append(f"({_MOMENTS[criteria.moment]})")
    return (  # nosec B608
        f"""
SELECT COALESCE(array_agg(x.start ORDER BY x.start), '{{}}') AS starts FROM (
    SELECT s.start FROM scheduling_slot s
    WHERE s.clinician_id = p.clinician_id AND s.appointment_type_id = p.type_id
      AND {" AND ".join(filters)}
    ORDER BY s.start LIMIT {limit}
) x
"""
    )


def _firsts(criteria: SearchCriteria) -> str:
    """Each provider with first free start and distance; time filters drop those without."""
    return (  # nosec B608
        f"""
SELECT p.*, n.starts[1] AS first_start,
       {_DISTANCE if criteria.location else "NULL::float8"} AS distance_km
FROM prov p
LEFT JOIN LATERAL ({_slots(criteria, limit=1)}) n ON true
{"WHERE cardinality(n.starts) > 0" if criteria.has_time_filter else ""}
"""
    )


def _order(criteria: SearchCriteria, soonest: str, name: str, ident: str, distance: str) -> str:
    # Ties break on name then id; the name order is case-insensitive.
    lowered = f"lower({name})"
    match criteria.sort:
        case Sort.NAME_ASC:
            return f"{lowered}, {name}, {ident}"
        case Sort.NAME_DESC:
            return f"{lowered} DESC, {name} DESC, {ident}"
        case Sort.DISTANCE:
            return f"{distance} NULLS LAST, {lowered}, {name}, {ident}"
        case Sort.SOONEST:
            return f"{soonest} NULLS LAST, {lowered}, {name}, {ident}"


def _paging(criteria: SearchCriteria) -> Params:
    return {"limit": criteria.size, "offset": (criteria.page - 1) * criteria.size}


def _distance(row: dict[str, Any]) -> float | None:
    return None if row["distance_km"] is None else float(row["distance_km"])


def _first(row: dict[str, Any]) -> FirstSlot | None:
    if row["first_start"] is None:
        return None
    return FirstSlot(
        start=row["first_start"],
        type_id=Id(row["type_id"]),
        type_name=row["type_name"],
        department_id=Id(row["department_id"]),
    )


def _provider(row: dict[str, Any]) -> ProviderResult:
    starts: Sequence[datetime] = row["starts"]
    next_slots = (
        NextSlots(Id(row["type_id"]), row["type_name"], row["duration_minutes"], tuple(starts))
        if starts
        else None
    )
    return ProviderResult(
        id=Id(row["clinician_id"]),
        full_name=row["full_name"],
        title=row["title"],
        specialty_name=row["specialty_name"],
        hospital_id=Id(row["hospital_id"]),
        hospital_name=row["hospital_name"],
        department_name=row["department_name"],
        city=row["city"],
        time_zone=row["time_zone"],
        next_slots=next_slots,
        distance_km=_distance(row),
    )


def _hospital(row: dict[str, Any]) -> HospitalResult:
    return HospitalResult(
        id=Id(row["hospital_id"]),
        name=row["hospital_name"],
        street=row["street"],
        postal_code=row["postal_code"],
        city=row["city"],
        time_zone=row["time_zone"],
        specialties=tuple(row["specialties"]),
        providers=row["providers"],
        providers_with_slots=row["with_slots"],
        first_slot=_first(row),
        distance_km=_distance(row),
    )


def _specialty(row: dict[str, Any]) -> SpecialtyResult:
    return SpecialtyResult(
        id=Id(row["specialty_id"]),
        name=row["specialty_name"],
        providers=row["providers"],
        hospitals=row["hospitals"],
        first_slot=_first(row),
        time_zone=row["time_zone"],
        distance_km=_distance(row),
    )
