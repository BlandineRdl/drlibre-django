from dataclasses import dataclass
from datetime import date, datetime, time

from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class HospitalRow:
    id: Id
    name: str
    code: str
    description: str
    street: str
    postal_code: str
    city: str
    country: str
    phone: str
    time_zone: str
    latitude: float | None
    longitude: float | None
    active: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DepartmentRow:
    """Active when its hospital is; its stamp is the later of both records."""

    id: Id
    hospital_id: Id
    name: str
    code: str
    description: str
    active: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RoomRow:
    id: Id
    department_id: Id
    hospital_id: Id
    name: str
    code: str
    floor: str
    capacity: int
    equipment: tuple[str, ...]
    active: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ServiceRow:
    """An appointment type, with the specialties of its department's clinicians."""

    id: Id
    department_id: Id
    name: str
    code: str
    duration_minutes: int
    buffer_minutes: int
    colour: str
    needs_room: bool
    bookable_online: bool
    active: bool
    specialty_ids: tuple[Id, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SpecialtyRow:
    id: Id
    name: str
    code: str
    active: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PractitionerRow:
    """A clinician or admin user; email and phone are None unless staff read them."""

    id: Id
    full_name: str
    title: str | None
    active: bool
    is_admin: bool
    email: str | None
    phone: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AvailabilityRow:
    """A rule as a role's weekly hours; weekday 0 is Sunday."""

    id: Id
    weekday: int
    start: time
    end: time
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TimeOffRow:
    id: Id
    start: datetime
    end: datetime
    reason: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RoleRow:
    """A clinician profile (id = profile) or an admin's role (id = user), with its hours."""

    id: Id
    practitioner_id: Id
    active: bool
    is_admin: bool
    department_id: Id | None
    hospital_id: Id | None
    specialty_id: Id | None
    default_room_id: Id | None
    bio: str
    weight: int | None
    service_ids: tuple[Id, ...]
    availability: tuple[AvailabilityRow, ...]
    time_offs: tuple[TimeOffRow, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    """An availability rule; active while its clinician is."""

    id: Id
    practitioner_id: Id
    role_id: Id
    room_id: Id | None
    weekday: int
    start: time
    end: time
    step_minutes: int
    valid_from: date
    valid_to: date | None
    active: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PatientRow:
    id: Id
    full_name: str
    email: str
    phone: str | None
    birth_date: date | None
    active: bool
    updated_at: datetime
