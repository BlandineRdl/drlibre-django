from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class BookableType:
    id: Id
    department_id: Id
    duration_minutes: int
    needs_room: bool
    bookable_online: bool
    active: bool


@dataclass(frozen=True, slots=True)
class BookableClinician:
    id: Id
    department_id: Id
    active: bool
    default_room_id: Id | None
    weight: int
    last_assigned_at: datetime | None


class Appointments(Protocol):
    def add(self, appointment: Appointment) -> None:
        """Store the appointment."""
        ...

    def conflicting_resources(
        self, *, clinician_id: Id, patient_id: Id, start: datetime, end: datetime
    ) -> tuple[str, ...]:
        """Names ("clinician", "patient") having an active appointment overlapping the range."""
        ...

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        """Future active ONLINE or ROUND_ROBIN appointments of the patient."""
        ...

    def busy_rooms(self, room_ids: tuple[Id, ...], start: datetime, end: datetime) -> frozenset[Id]:
        """The given rooms used by an active appointment overlapping the range."""
        ...


class BookingDirectory(Protocol):
    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        """The type, active or not, or None when unknown."""
        ...

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        """The clinician profile, active or not, or None when unknown."""
        ...

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        """The department's active rooms in code order."""
        ...


class FreeSlots(Protocol):
    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
    ) -> bool:
        """Whether the start is exactly one of the clinician's free slots for the type."""
        ...

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        """Active clinicians of the type's department with a free slot at the start."""
        ...


class SlotRefresh(Protocol):
    def refresh(self, clinician_id: Id) -> None:
        """Rebuild the clinician's stored slots, in the caller's unit of work."""
        ...


class ScheduleLocks(Protocol):
    def lock_clinician(self, clinician_id: Id) -> None:
        """Hold the clinician's writes until the caller's unit ends; unknown ids lock nothing."""
        ...

    def lock_patient(self, patient_id: Id) -> None:
        """Hold the patient's bookings until the caller's unit ends; unknown ids lock nothing."""
        ...


class Patients(Protocol):
    def is_active(self, patient_id: Id) -> bool:
        """Whether the id is an active patient."""
        ...


class BookingNotices(Protocol):
    def confirmed(self, appointment: Appointment) -> None:
        """Queue the confirmation for the patient, sent once the unit of work commits."""
        ...


class RoundRobinLedger(Protocol):
    def record(self, clinician_id: Id, at: datetime) -> None:
        """Set the clinician's last round robin assignment, in the caller's unit of work."""
        ...
