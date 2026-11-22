from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum

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


class AppointmentKind(StrEnum):
    """The record an `Appointment` resource stands for."""

    APPOINTMENT = "appointment"
    WAITLIST = "waitlist"
    HOLD = "hold"


HELD = "HELD"


@dataclass(frozen=True, slots=True)
class AppointmentRow:
    """An appointment, a waitlist entry not yet booked or an open hold, as its reader sees it."""

    id: Id
    kind: AppointmentKind
    # The record's own status: an appointment's, an entry's, or HELD for a hold.
    status: str
    patient_id: Id | None
    # An offered entry's offered clinician, a waiting one's preferred clinician; a profile id.
    clinician_id: Id | None
    practitioner_id: Id | None
    appointment_type_id: Id
    room_id: Id | None
    # An offered entry's offered start and end; none for a waiting entry.
    start: datetime | None
    end: datetime | None
    # A waitlist entry's window.
    earliest: datetime | None
    latest: datetime | None
    source: str | None
    reason: str | None
    cancellation_reason: str | None
    # Filled for the appointment's own clinician only.
    clinical_notes: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AppointmentResponseRow:
    """A booked waitlist entry: its patient accepted the appointment of the same id."""

    id: Id
    patient_id: Id
    updated_at: datetime
