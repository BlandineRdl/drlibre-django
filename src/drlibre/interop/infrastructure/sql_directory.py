# SQL is composed from fixed fragments only; every value is a bound parameter.
import json
import uuid
from datetime import datetime, time
from typing import Any

from django.db import connection

from drlibre.interop.application.ports.inbound import DirectoryQueries
from drlibre.interop.domain.filters import (
    LocationFilter,
    OrganizationFilter,
    Paging,
    PractitionerFilter,
    RoleFilter,
    ScheduleFilter,
    ServiceFilter,
    SpecialtyFilter,
)
from drlibre.interop.domain.reader import Reader
from drlibre.interop.domain.rows import (
    AvailabilityRow,
    DepartmentRow,
    HospitalRow,
    PractitionerRow,
    RoleRow,
    RoomRow,
    ScheduleRow,
    ServiceRow,
    SpecialtyRow,
    TimeOffRow,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

type Row = dict[str, Any]

_ORGANIZATIONS = """
SELECT 'hospital' AS kind, h.id, NULL::uuid AS hospital_id, h.name, h.code, h.description,
       h.street, h.postal_code, h.city, h.country, h.phone, h.time_zone, h.latitude,
       h.longitude, h.active, h.updated_at
FROM organisation_hospitalrecord h
UNION ALL
SELECT 'department', d.id, d.hospital_id, d.name, d.code, d.description,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, h.active,
       greatest(d.updated_at, h.updated_at)
FROM organisation_departmentrecord d
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
"""

_LOCATIONS = """
SELECT 'site' AS kind, h.id, NULL::uuid AS department_id, h.id AS hospital_id, h.name, h.code,
       h.description, h.street, h.postal_code, h.city, h.country, h.phone, h.time_zone,
       h.latitude, h.longitude, NULL::varchar AS floor, NULL::integer AS capacity,
       NULL::jsonb AS equipment, h.active, h.updated_at
FROM organisation_hospitalrecord h
UNION ALL
SELECT 'room', r.id, r.department_id, d.hospital_id, r.name, r.code,
       '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, r.floor, r.capacity,
       r.equipment, r.active AND h.active, greatest(r.updated_at, h.updated_at)
FROM organisation_roomrecord r
JOIN organisation_departmentrecord d ON d.id = r.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
"""

_DISTANCE = """
2 * 6371 * asin(least(1, sqrt(
    power(sin(radians(o.latitude - %(lat)s::float8) / 2), 2)
    + cos(radians(%(lat)s::float8)) * cos(radians(o.latitude))
      * power(sin(radians(o.longitude - %(lon)s::float8) / 2), 2))))
"""

_SERVICES = """
SELECT t.id, t.department_id, d.hospital_id, t.name, t.code, t.duration_minutes,
       t.buffer_minutes, t.colour, t.needs_room, t.bookable_online, t.active AND h.active AS active,
       ARRAY(SELECT DISTINCT c.specialty_id FROM organisation_clinicianprofilerecord c
             WHERE c.department_id = t.department_id) AS specialty_ids,
       greatest(t.updated_at, h.updated_at) AS updated_at
FROM organisation_appointmenttyperecord t
JOIN organisation_departmentrecord d ON d.id = t.department_id
JOIN organisation_hospitalrecord h ON h.id = d.hospital_id
"""

_PRACTITIONERS = """
SELECT u.id, u.full_name AS name, p.title, u.active, u.role = 'ADMIN' AS is_admin, u.email,
       u.phone, greatest(u.updated_at, p.updated_at) AS updated_at
FROM identity_userrecord u
LEFT JOIN organisation_clinicianprofilerecord p ON p.user_id = u.id
WHERE u.role = 'CLINICIAN' {admins}
"""

_ROLES = """
SELECT p.id, u.id AS practitioner_id, u.full_name AS name, u.active, false AS is_admin,
       p.department_id, d.hospital_id, p.specialty_id, p.default_room_id, p.bio, p.weight,
       ARRAY(SELECT t.id FROM organisation_appointmenttyperecord t
             WHERE t.department_id = p.department_id AND t.active {online}
             ORDER BY t.name, t.id) AS service_ids,
       (SELECT coalesce(json_agg(json_build_object(
                   'id', a.id, 'weekday', a.weekday, 'start', a.start, 'end', a."end",
                   'updated_at', a.updated_at) ORDER BY a.weekday, a.start, a.id), '[]')
        FROM scheduling_availabilityrulemodel a WHERE a.clinician_id = p.id) AS availability,
       (SELECT coalesce(json_agg(json_build_object(
                   'id', o.id, 'start', o.start, 'end', o."end", 'reason', o.reason,
                   'updated_at', o.updated_at) ORDER BY o.start, o.id), '[]')
        FROM scheduling_timeoffmodel o WHERE o.clinician_id = p.id) AS time_offs,
       greatest(p.updated_at, u.updated_at) AS updated_at
FROM organisation_clinicianprofilerecord p
JOIN identity_userrecord u ON u.id = p.user_id
JOIN organisation_departmentrecord d ON d.id = p.department_id
"""

_ADMIN_ROLES = """
UNION ALL
SELECT u.id, u.id, u.full_name, u.active, true, NULL, NULL, NULL, NULL, '', NULL,
       ARRAY[]::uuid[], '[]'::json, '[]'::json, u.updated_at
FROM identity_userrecord u WHERE u.role = 'ADMIN'
"""

_SCHEDULES = """
SELECT a.id, u.id AS practitioner_id, p.id AS role_id, a.room_id, a.weekday, a.start, a."end",
       a.step_minutes, a.valid_from, a.valid_to, u.active,
       greatest(a.updated_at, u.updated_at) AS updated_at
FROM scheduling_availabilityrulemodel a
JOIN organisation_clinicianprofilerecord p ON p.id = a.clinician_id
JOIN identity_userrecord u ON u.id = p.user_id
"""


def like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class Where:
    """Conditions on the `o` relation and their bound values."""

    def __init__(self, ids: tuple[Id, ...]) -> None:
        self.conditions: list[str] = []
        self.params: dict[str, Any] = {}
        if ids:
            self.add("o.id = ANY(%(ids)s::uuid[])", ids=[i.value for i in ids])

    def add(self, condition: str, **params: Any) -> None:
        self.conditions.append(condition)
        self.params |= params

    def when(self, value: object, condition: str, name: str) -> None:
        if value is not None:
            self.add(condition, **{name: value.value if isinstance(value, Id) else value})

    def sql(self) -> str:
        return " AND ".join(self.conditions) or "true"


def page_of(
    relation: str, where: Where, paging: Paging | None, order: tuple[str, ...]
) -> tuple[list[Row], int]:
    direction = "DESC" if paging and paging.descending else "ASC"
    ordering = ", ".join(f"o.{column} {direction}" for column in order)
    limit = "LIMIT %(limit)s OFFSET %(offset)s" if paging else ""
    head = ("SELECT o.*, COUNT(*) OVER () AS total FROM (", relation, ") o WHERE")
    sql = " ".join((*head, where.sql(), "ORDER BY", ordering, limit))
    params = where.params | ({"limit": paging.count, "offset": paging.offset} if paging else {})
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column.name for column in cursor.description or ()]
        rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    return rows, int(rows[0]["total"]) if rows else 0


def _number(paging: Paging | None) -> int:
    return paging.page if paging else 1


def _loaded(value: Any) -> Any:
    """Django leaves json and jsonb columns as text."""
    return json.loads(value) if isinstance(value, str) else value


def _id(value: Any) -> Id:
    return Id(value if isinstance(value, uuid.UUID) else uuid.UUID(value))


def _hospital(row: Row) -> HospitalRow:
    return HospitalRow(
        id=Id(row["id"]),
        name=row["name"],
        code=row["code"],
        description=row["description"],
        street=row["street"],
        postal_code=row["postal_code"],
        city=row["city"],
        country=row["country"],
        phone=row["phone"],
        time_zone=row["time_zone"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        active=row["active"],
        updated_at=row["updated_at"],
    )


def _department(row: Row) -> DepartmentRow:
    return DepartmentRow(
        id=Id(row["id"]),
        hospital_id=Id(row["hospital_id"]),
        name=row["name"],
        code=row["code"],
        description=row["description"],
        active=row["active"],
        updated_at=row["updated_at"],
    )


def _room(row: Row) -> RoomRow:
    return RoomRow(
        id=Id(row["id"]),
        department_id=Id(row["department_id"]),
        hospital_id=Id(row["hospital_id"]),
        name=row["name"],
        code=row["code"],
        floor=row["floor"],
        capacity=row["capacity"],
        equipment=tuple(_loaded(row["equipment"])),
        active=row["active"],
        updated_at=row["updated_at"],
    )


def _role(row: Row, reader: Reader) -> RoleRow:
    return RoleRow(
        id=Id(row["id"]),
        practitioner_id=Id(row["practitioner_id"]),
        active=row["active"],
        is_admin=row["is_admin"],
        department_id=Id(row["department_id"]) if row["department_id"] else None,
        hospital_id=Id(row["hospital_id"]) if row["hospital_id"] else None,
        specialty_id=Id(row["specialty_id"]) if row["specialty_id"] else None,
        default_room_id=Id(row["default_room_id"]) if row["default_room_id"] else None,
        bio=row["bio"],
        weight=row["weight"] if reader.is_staff else None,
        service_ids=tuple(map(Id, row["service_ids"])),
        availability=tuple(
            AvailabilityRow(
                id=_id(a["id"]),
                weekday=a["weekday"],
                start=time.fromisoformat(a["start"]),
                end=time.fromisoformat(a["end"]),
                updated_at=datetime.fromisoformat(a["updated_at"]),
            )
            for a in _loaded(row["availability"])
        ),
        time_offs=tuple(
            TimeOffRow(
                id=_id(o["id"]),
                start=datetime.fromisoformat(o["start"]),
                end=datetime.fromisoformat(o["end"]),
                reason=o["reason"] if reader.is_staff else None,
                updated_at=datetime.fromisoformat(o["updated_at"]),
            )
            for o in _loaded(row["time_offs"])
        ),
        updated_at=row["updated_at"],
    )


class SqlDirectoryQueries(DirectoryQueries):
    """Reads the organisation, identity and scheduling tables, one statement per search."""

    def organizations(
        self, criteria: OrganizationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | DepartmentRow]:
        where = Where(criteria.ids)
        if not reader.is_admin:
            where.add("o.active")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(criteria.kind and criteria.kind.value, "o.kind = %(kind)s", "kind")
        where.when(criteria.part_of, "o.hospital_id = %(part_of)s", "part_of")
        where.when(criteria.city and like(criteria.city), "o.city ILIKE %(city)s", "city")
        where.when(criteria.active, "o.active = %(active)s", "active")
        rows, total = page_of(_ORGANIZATIONS, where, paging, ("name", "id"))
        items = tuple(_hospital(r) if r["kind"] == "hospital" else _department(r) for r in rows)
        return Page(items, total, _number(paging))

    def locations(
        self, criteria: LocationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | RoomRow]:
        where = Where(criteria.ids)
        if not reader.is_admin:
            where.add("o.active")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(criteria.kind and criteria.kind.value, "o.kind = %(kind)s", "kind")
        where.when(
            criteria.organization,
            "((o.kind = 'site' AND o.id = %(org)s) OR o.department_id = %(org)s)",
            "org",
        )
        where.when(criteria.part_of, "o.kind = 'room' AND o.hospital_id = %(part_of)s", "part_of")
        where.when(criteria.city and like(criteria.city), "o.city ILIKE %(city)s", "city")
        where.when(criteria.active, "o.active = %(active)s", "active")
        if criteria.near:
            near = criteria.near
            where.add(
                f"o.latitude IS NOT NULL AND o.longitude IS NOT NULL AND {_DISTANCE} <= %(km)s",
                lat=near.latitude,
                lon=near.longitude,
                km=near.km,
            )
        rows, total = page_of(_LOCATIONS, where, paging, ("name", "id"))
        items = tuple(_hospital(r) if r["kind"] == "site" else _room(r) for r in rows)
        return Page(items, total, _number(paging))

    def services(
        self, criteria: ServiceFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ServiceRow]:
        where = Where(criteria.ids)
        if not reader.is_admin:
            where.add("o.active")
        if not reader.is_staff:
            where.add("o.bookable_online")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(
            criteria.organization,
            "(o.department_id = %(org)s OR o.hospital_id = %(org)s)",
            "org",
        )
        where.when(criteria.specialty, "%(specialty)s = ANY(o.specialty_ids)", "specialty")
        where.when(criteria.active, "o.active = %(active)s", "active")
        rows, total = page_of(_SERVICES, where, paging, ("name", "id"))
        items = tuple(
            ServiceRow(
                id=Id(r["id"]),
                department_id=Id(r["department_id"]),
                name=r["name"],
                code=r["code"],
                duration_minutes=r["duration_minutes"],
                buffer_minutes=r["buffer_minutes"],
                colour=r["colour"],
                needs_room=r["needs_room"],
                bookable_online=r["bookable_online"],
                active=r["active"],
                specialty_ids=tuple(sorted(map(Id, r["specialty_ids"]), key=str)),
                updated_at=r["updated_at"],
            )
            for r in rows
        )
        return Page(items, total, _number(paging))

    def specialties(
        self, criteria: SpecialtyFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[SpecialtyRow]:
        where = Where(criteria.ids)
        if not reader.is_admin:
            where.add("o.active")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(criteria.active, "o.active = %(active)s", "active")
        relation = "SELECT id, name, code, active, updated_at FROM organisation_specialtyrecord"
        rows, total = page_of(relation, where, paging, ("name", "id"))
        items = tuple(
            SpecialtyRow(Id(r["id"]), r["name"], r["code"], r["active"], r["updated_at"])
            for r in rows
        )
        return Page(items, total, _number(paging))

    def practitioners(
        self, criteria: PractitionerFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PractitionerRow]:
        where = Where(criteria.ids)
        if not reader.is_staff:
            where.add("o.active")
        where.when(criteria.name and like(criteria.name), "o.name ILIKE %(name)s", "name")
        where.when(criteria.active, "o.active = %(active)s", "active")
        relation = _PRACTITIONERS.format(admins="OR u.role = 'ADMIN'" if reader.is_admin else "")
        rows, total = page_of(relation, where, paging, ("name", "id"))
        items = tuple(
            PractitionerRow(
                id=Id(r["id"]),
                full_name=r["name"],
                title=r["title"],
                active=r["active"],
                is_admin=r["is_admin"],
                email=r["email"] if reader.is_staff else None,
                phone=r["phone"] if reader.is_staff else None,
                updated_at=r["updated_at"],
            )
            for r in rows
        )
        return Page(items, total, _number(paging))

    def roles(
        self, criteria: RoleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[RoleRow]:
        where = Where(criteria.ids)
        if not reader.is_staff:
            where.add("o.active")
        where.when(criteria.practitioner, "o.practitioner_id = %(practitioner)s", "practitioner")
        where.when(
            criteria.organization,
            "(o.department_id = %(org)s OR o.hospital_id = %(org)s)",
            "org",
        )
        where.when(criteria.specialty, "o.specialty_id = %(specialty)s", "specialty")
        where.when(
            criteria.location,
            "(o.hospital_id = %(location)s OR o.default_room_id = %(location)s)",
            "location",
        )
        where.when(criteria.service, "%(service)s = ANY(o.service_ids)", "service")
        where.when(criteria.active, "o.active = %(active)s", "active")
        relation = _ROLES.format(online="" if reader.is_staff else "AND t.bookable_online") + (
            _ADMIN_ROLES if reader.is_admin else ""
        )
        rows, total = page_of(relation, where, paging, ("name", "id"))
        return Page(tuple(_role(r, reader) for r in rows), total, _number(paging))

    def schedules(
        self, criteria: ScheduleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ScheduleRow]:
        where = Where(criteria.ids)
        if not reader.is_staff:
            where.add("o.active")
        where.when(
            criteria.actor, "(o.practitioner_id = %(actor)s OR o.room_id = %(actor)s)", "actor"
        )
        where.when(criteria.starts_by, "o.valid_from <= %(starts_by)s", "starts_by")
        where.when(
            criteria.ends_from, "(o.valid_to IS NULL OR o.valid_to >= %(ends_from)s)", "ends_from"
        )
        where.when(criteria.active, "o.active = %(active)s", "active")
        rows, total = page_of(_SCHEDULES, where, paging, ("weekday", "start", "id"))
        items = tuple(
            ScheduleRow(
                id=Id(r["id"]),
                practitioner_id=Id(r["practitioner_id"]),
                role_id=Id(r["role_id"]),
                room_id=Id(r["room_id"]) if r["room_id"] else None,
                weekday=r["weekday"],
                start=r["start"],
                end=r["end"],
                step_minutes=r["step_minutes"],
                valid_from=r["valid_from"],
                valid_to=r["valid_to"],
                active=r["active"],
                updated_at=r["updated_at"],
            )
            for r in rows
        )
        return Page(items, total, _number(paging))
