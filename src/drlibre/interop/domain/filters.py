from dataclasses import dataclass
from datetime import date, datetime
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


@dataclass(frozen=True, slots=True)
class AppointmentFilter:
    """`practitioner` is a clinician's user; `statuses` pairs a record kind with its own status."""

    ids: tuple[Id, ...] = ()
    patient: Id | None = None
    practitioner: Id | None = None
    room: Id | None = None
    appointment_type: Id | None = None
    statuses: tuple[tuple[str, str], ...] = ()
    # The start lies from `start_from` included to `start_before` excluded.
    start_from: datetime | None = None
    start_before: datetime | None = None


@dataclass(frozen=True, slots=True)
class AppointmentResponseFilter:
    """An `AppointmentResponse` shares its id with the entry and the appointment it accepted."""

    ids: tuple[Id, ...] = ()
    patient: Id | None = None


@dataclass(frozen=True, slots=True)
class CommunicationFilter:
    """`category` is a notification kind; `sent` lies from `sent_from` to `sent_before` excluded."""

    ids: tuple[Id, ...] = ()
    recipient: Id | None = None
    category: str | None = None
    sent_from: datetime | None = None
    sent_before: datetime | None = None


class AuditAction(StrEnum):
    """FHIR `AuditEvent.action`, read from the product action's suffix; E for any other."""

    CREATE = "C"
    READ = "R"
    UPDATE = "U"
    DELETE = "D"
    EXECUTE = "E"

    @classmethod
    def of(cls, action: str) -> "AuditAction":
        suffix = action.rpartition(".")[2]
        return _SUFFIXES.get(suffix, cls.EXECUTE)


_SUFFIXES = {
    "created": AuditAction.CREATE,
    "updated": AuditAction.UPDATE,
    "deleted": AuditAction.DELETE,
}


@dataclass(frozen=True, slots=True)
class AuditEventFilter:
    """`agent` is the actor's user; `at` lies from `at_from` to `at_before` excluded."""

    ids: tuple[Id, ...] = ()
    agent: Id | None = None
    entity: Id | None = None
    entity_type: str | None = None
    actions: tuple[AuditAction, ...] = ()
    at_from: datetime | None = None
    at_before: datetime | None = None
