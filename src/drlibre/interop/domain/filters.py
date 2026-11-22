from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Paging:
    """One page of rows ordered by name then id; descending reverses both."""

    count: int = 20
    page: int = 1
    descending: bool = False

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.count


class OrganizationKind(StrEnum):
    HOSPITAL = "hospital"
    DEPARTMENT = "department"


class LocationKind(StrEnum):
    SITE = "site"
    ROOM = "room"


@dataclass(frozen=True, slots=True)
class Near:
    latitude: float
    longitude: float
    km: float


@dataclass(frozen=True, slots=True)
class OrganizationFilter:
    ids: tuple[Id, ...] = ()
    name: str | None = None
    kind: OrganizationKind | None = None
    part_of: Id | None = None
    city: str | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class LocationFilter:
    """`organization` is a site's hospital or a room's department; `part_of` a room's site."""

    ids: tuple[Id, ...] = ()
    name: str | None = None
    kind: LocationKind | None = None
    organization: Id | None = None
    part_of: Id | None = None
    city: str | None = None
    near: Near | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class ServiceFilter:
    ids: tuple[Id, ...] = ()
    name: str | None = None
    organization: Id | None = None
    specialty: Id | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class SpecialtyFilter:
    ids: tuple[Id, ...] = ()
    name: str | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class PractitionerFilter:
    ids: tuple[Id, ...] = ()
    name: str | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class RoleFilter:
    """`organization` is a department or its hospital; `location` a site or a default room."""

    ids: tuple[Id, ...] = ()
    practitioner: Id | None = None
    organization: Id | None = None
    specialty: Id | None = None
    location: Id | None = None
    service: Id | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class ScheduleFilter:
    """`actor` is a clinician user or a room; a horizon starting by and ending from a day."""

    ids: tuple[Id, ...] = ()
    actor: Id | None = None
    starts_by: date | None = None
    ends_from: date | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class PatientFilter:
    """`name` is a part of the name; `email` and `phone` match whole, `birth_date` the day."""

    ids: tuple[Id, ...] = ()
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
