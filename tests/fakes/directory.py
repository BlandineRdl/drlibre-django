import math
from collections.abc import Callable, Iterable
from datetime import datetime

from drlibre.identity.domain.user import Role, User
from drlibre.interop.application.ports.inbound import DirectoryQueries
from drlibre.interop.domain.filters import (
    LocationFilter,
    LocationKind,
    OrganizationFilter,
    OrganizationKind,
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
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.hospital import Hospital
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.fakes.organisation import (
    InMemoryAppointmentTypes,
    InMemoryClinicianProfiles,
    InMemoryDepartments,
    InMemoryHospitals,
    InMemoryRooms,
    InMemorySpecialties,
)
from tests.fakes.scheduling import InMemoryAvailabilityRules, InMemoryTimeOffs
from tests.fakes.users import InMemoryUsers


def _page[T](
    rows: Iterable[T],
    keep: Callable[[T], bool],
    key: Callable[[T], tuple[object, ...]],
    paging: Paging | None,
) -> Page[T]:
    found = sorted(
        (r for r in rows if keep(r)), key=key, reverse=bool(paging and paging.descending)
    )
    if paging is None:
        return Page(tuple(found), len(found), 1)
    return Page(tuple(found[paging.offset : paging.offset + paging.count]), len(found), paging.page)


def _named(row: object) -> tuple[object, ...]:
    return (getattr(row, "name", ""), str(getattr(row, "id", "")))


def _has(text: str | None, value: str | None) -> bool:
    return text is None or (value is not None and text.lower() in value.lower())


def _is(wanted: object, value: object) -> bool:
    return wanted is None or wanted == value


def _km(lat: float, lon: float, row: HospitalRow) -> float:
    if row.latitude is None or row.longitude is None:
        return math.inf
    a = (
        math.sin(math.radians(row.latitude - lat) / 2) ** 2
        + math.cos(math.radians(lat))
        * math.cos(math.radians(row.latitude))
        * math.sin(math.radians(row.longitude - lon) / 2) ** 2
    )
    return 2 * 6371 * math.asin(min(1, math.sqrt(a)))


class InMemoryDirectoryQueries(DirectoryQueries):
    """Reads the world's organisation, user and scheduling fakes; rules carry `stamp`."""

    def __init__(
        self,
        *,
        hospitals: InMemoryHospitals,
        departments: InMemoryDepartments,
        rooms: InMemoryRooms,
        appointment_types: InMemoryAppointmentTypes,
        specialties: InMemorySpecialties,
        profiles: InMemoryClinicianProfiles,
        users: InMemoryUsers,
        rules: InMemoryAvailabilityRules,
        time_offs: InMemoryTimeOffs,
        stamp: datetime,
    ) -> None:
        self._hospitals = hospitals
        self._departments = departments
        self._rooms = rooms
        self._types = appointment_types
        self._specialties = specialties
        self._profiles = profiles
        self._users = users
        self._rules = rules
        self._time_offs = time_offs
        self._stamp = stamp

    def _hospital(self, hospital_id: Id) -> Hospital:
        found = self._hospitals.get(hospital_id)
        assert found is not None
        return found

    def _site(self, h: Hospital) -> HospitalRow:
        return HospitalRow(
            id=h.id,
            name=h.name,
            code=h.code,
            description=h.description,
            street=h.street,
            postal_code=h.postal_code,
            city=h.city,
            country=h.country,
            phone=h.phone,
            time_zone=h.time_zone,
            latitude=h.latitude,
            longitude=h.longitude,
            active=h.active,
            updated_at=h.updated_at,
        )

    def _departments_rows(self) -> list[DepartmentRow]:
        rows = []
        for d in self._departments.rows.values():
            h = self._hospital(d.hospital_id)
            stamp = max(d.updated_at, h.updated_at)
            rows.append(
                DepartmentRow(d.id, d.hospital_id, d.name, d.code, d.description, h.active, stamp)
            )
        return rows

    def organizations(
        self, criteria: OrganizationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | DepartmentRow]:
        sites: list[HospitalRow | DepartmentRow] = [
            self._site(h) for h in self._hospitals.rows.values()
        ]
        rows = sites + list(self._departments_rows())

        def keep(r: HospitalRow | DepartmentRow) -> bool:
            hospital = isinstance(r, HospitalRow)
            kind = OrganizationKind.HOSPITAL if hospital else OrganizationKind.DEPARTMENT
            return (
                (reader.is_admin or r.active)
                and (not criteria.ids or r.id in criteria.ids)
                and _has(criteria.name, r.name)
                and _is(criteria.kind, kind)
                and (
                    criteria.part_of is None or getattr(r, "hospital_id", None) == criteria.part_of
                )
                and (criteria.city is None or (hospital and _has(criteria.city, r.city)))
                and _is(criteria.active, r.active)
            )

        return _page(rows, keep, _named, paging)

    def locations(
        self, criteria: LocationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | RoomRow]:
        rows: list[HospitalRow | RoomRow] = [self._site(h) for h in self._hospitals.rows.values()]
        for r in self._rooms.rows.values():
            department = self._departments.get(r.department_id)
            assert department is not None
            h = self._hospital(department.hospital_id)
            rows.append(
                RoomRow(
                    id=r.id,
                    department_id=r.department_id,
                    hospital_id=h.id,
                    name=r.name,
                    code=r.code,
                    floor=r.floor,
                    capacity=r.capacity,
                    equipment=r.equipment,
                    active=r.active and h.active,
                    updated_at=max(r.updated_at, h.updated_at),
                )
            )

        def keep(r: HospitalRow | RoomRow) -> bool:
            site = isinstance(r, HospitalRow)
            near = criteria.near
            return (
                (reader.is_admin or r.active)
                and (not criteria.ids or r.id in criteria.ids)
                and _has(criteria.name, r.name)
                and _is(criteria.kind, LocationKind.SITE if site else LocationKind.ROOM)
                and (
                    criteria.organization is None
                    or (r.id if site else r.department_id) == criteria.organization
                )
                and (criteria.part_of is None or (not site and r.hospital_id == criteria.part_of))
                and (criteria.city is None or (site and _has(criteria.city, r.city)))
                and _is(criteria.active, r.active)
                and (near is None or (site and _km(near.latitude, near.longitude, r) <= near.km))
            )

        return _page(rows, keep, _named, paging)

    def services(
        self, criteria: ServiceFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ServiceRow]:
        rows = []
        for t in self._types.rows.values():
            department = self._departments.get(t.department_id)
            assert department is not None
            h = self._hospital(department.hospital_id)
            specialties = {
                p.specialty_id
                for p in self._profiles.rows.values()
                if p.department_id == t.department_id
            }
            rows.append(
                (
                    h.id,
                    ServiceRow(
                        id=t.id,
                        department_id=t.department_id,
                        name=t.name,
                        code=t.code,
                        duration_minutes=t.duration_minutes,
                        buffer_minutes=t.buffer_minutes,
                        colour=t.colour,
                        needs_room=t.needs_room,
                        bookable_online=t.bookable_online,
                        active=t.active and h.active,
                        specialty_ids=tuple(sorted(specialties, key=str)),
                        updated_at=max(t.updated_at, h.updated_at),
                    ),
                )
            )

        def keep(pair: tuple[Id, ServiceRow]) -> bool:
            hospital_id, r = pair
            return (
                (reader.is_admin or r.active)
                and (reader.is_staff or r.bookable_online)
                and (not criteria.ids or r.id in criteria.ids)
                and _has(criteria.name, r.name)
                and (criteria.organization in (None, r.department_id, hospital_id))
                and (criteria.specialty is None or criteria.specialty in r.specialty_ids)
                and _is(criteria.active, r.active)
            )

        page = _page(rows, keep, lambda pair: _named(pair[1]), paging)
        return Page(tuple(r for _, r in page.items), page.total, page.number)

    def specialties(
        self, criteria: SpecialtyFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[SpecialtyRow]:
        rows = [
            SpecialtyRow(s.id, s.name, s.code, s.active, s.updated_at)
            for s in self._specialties.rows.values()
        ]

        def keep(r: SpecialtyRow) -> bool:
            return (
                (reader.is_admin or r.active)
                and (not criteria.ids or r.id in criteria.ids)
                and _has(criteria.name, r.name)
                and _is(criteria.active, r.active)
            )

        return _page(rows, keep, _named, paging)

    def _staff_users(self, reader: Reader) -> list[tuple[User, ClinicianProfile | None]]:
        roles = {Role.CLINICIAN, Role.ADMIN} if reader.is_admin else {Role.CLINICIAN}
        return [
            (u, self._profiles.for_user(u.id))
            for u in self._users.rows.values()
            if u.role in roles and (reader.is_staff or u.active)
        ]

    def practitioners(
        self, criteria: PractitionerFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PractitionerRow]:
        rows = [
            PractitionerRow(
                id=u.id,
                full_name=u.full_name,
                title=p.title if p else None,
                active=u.active,
                is_admin=u.role is Role.ADMIN,
                email=u.email.value if reader.is_staff else None,
                phone=u.phone if reader.is_staff else None,
                updated_at=max(u.updated_at, p.updated_at) if p else u.updated_at,
            )
            for u, p in self._staff_users(reader)
        ]

        def keep(r: PractitionerRow) -> bool:
            return (
                (not criteria.ids or r.id in criteria.ids)
                and _has(criteria.name, r.full_name)
                and _is(criteria.active, r.active)
            )

        return _page(rows, keep, lambda r: (r.full_name, str(r.id)), paging)

    def _role(self, u: User, p: ClinicianProfile, reader: Reader) -> tuple[str, RoleRow]:
        department = self._departments.get(p.department_id)
        assert department is not None
        services = sorted(
            (
                t
                for t in self._types.rows.values()
                if t.department_id == p.department_id
                and t.active
                and (reader.is_staff or t.bookable_online)
            ),
            key=_named,
        )
        rules = sorted(
            (r for r in self._rules.rows.values() if r.clinician_id == p.id),
            key=lambda r: (r.weekday, r.start, str(r.id)),
        )
        offs = sorted(
            (o for o in self._time_offs.rows.values() if o.clinician_id == p.id),
            key=lambda o: (o.start, str(o.id)),
        )
        return u.full_name, RoleRow(
            id=p.id,
            practitioner_id=u.id,
            active=u.active,
            is_admin=False,
            department_id=p.department_id,
            hospital_id=department.hospital_id,
            specialty_id=p.specialty_id,
            default_room_id=p.default_room_id,
            bio=p.bio,
            weight=p.weight if reader.is_staff else None,
            service_ids=tuple(t.id for t in services),
            availability=tuple(
                AvailabilityRow(r.id, r.weekday, r.start, r.end, self._stamp) for r in rules
            ),
            time_offs=tuple(
                TimeOffRow(o.id, o.start, o.end, o.reason if reader.is_staff else None, self._stamp)
                for o in offs
            ),
            updated_at=max(p.updated_at, u.updated_at),
        )

    def roles(
        self, criteria: RoleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[RoleRow]:
        rows: list[tuple[str, RoleRow]] = []
        for u, p in self._staff_users(reader):
            if p is not None:
                rows.append(self._role(u, p, reader))
            elif u.role is Role.ADMIN:
                admin = RoleRow(
                    u.id,
                    u.id,
                    u.active,
                    True,
                    None,
                    None,
                    None,
                    None,
                    "",
                    None,
                    (),
                    (),
                    (),
                    u.updated_at,
                )
                rows.append((u.full_name, admin))

        def keep(pair: tuple[str, RoleRow]) -> bool:
            r = pair[1]
            return (
                (not criteria.ids or r.id in criteria.ids)
                and _is(criteria.practitioner, r.practitioner_id)
                and (criteria.organization in (None, r.department_id, r.hospital_id))
                and _is(criteria.specialty, r.specialty_id)
                and (criteria.location in (None, r.hospital_id, r.default_room_id))
                and (criteria.service is None or criteria.service in r.service_ids)
                and _is(criteria.active, r.active)
            )

        page = _page(rows, keep, lambda pair: (pair[0], str(pair[1].id)), paging)
        return Page(tuple(r for _, r in page.items), page.total, page.number)

    def schedules(
        self, criteria: ScheduleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ScheduleRow]:
        rows = []
        for rule in self._rules.rows.values():
            profile = self._profiles.get(rule.clinician_id)
            assert profile is not None
            user = self._users.get(profile.user_id)
            assert user is not None
            rows.append(
                ScheduleRow(
                    id=rule.id,
                    practitioner_id=user.id,
                    role_id=profile.id,
                    room_id=rule.room_id,
                    weekday=rule.weekday,
                    start=rule.start,
                    end=rule.end,
                    step_minutes=rule.step_minutes,
                    valid_from=rule.valid_from,
                    valid_to=rule.valid_to,
                    active=user.active,
                    updated_at=max(self._stamp, user.updated_at),
                )
            )

        def keep(r: ScheduleRow) -> bool:
            return (
                (reader.is_staff or r.active)
                and (not criteria.ids or r.id in criteria.ids)
                and (criteria.actor in (None, r.practitioner_id, r.room_id))
                and (criteria.starts_by is None or r.valid_from <= criteria.starts_by)
                and (
                    criteria.ends_from is None
                    or r.valid_to is None
                    or r.valid_to >= criteria.ends_from
                )
                and _is(criteria.active, r.active)
            )

        return _page(rows, keep, lambda r: (r.weekday, r.start, str(r.id)), paging)
