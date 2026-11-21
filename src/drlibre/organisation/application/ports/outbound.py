from dataclasses import dataclass
from typing import Protocol

from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class Records[T](Protocol):
    def get(self, record_id: Id) -> T | None:
        """Return the record, or None when absent."""
        ...

    def save(self, record: T) -> None:
        """Insert or replace the record by id."""
        ...

    def delete(self, record_id: Id) -> None:
        """Remove the record; callers check its dependents first."""
        ...

    def code_taken(self, code: str, *, except_id: Id) -> bool:
        """True when another record of this kind already holds the code."""
        ...


class Hospitals(Records[Hospital], Protocol):
    pass


class Specialties(Records[Specialty], Protocol):
    pass


class Departments(Records[Department], Protocol):
    def for_hospital(self, hospital_id: Id) -> tuple[Department, ...]:
        """Return the departments of the hospital, by name."""
        ...


class Rooms(Records[Room], Protocol):
    def for_department(self, department_id: Id) -> tuple[Room, ...]:
        """Return the rooms of the department, by name."""
        ...


class AppointmentTypes(Records[AppointmentType], Protocol):
    def for_department(self, department_id: Id) -> tuple[AppointmentType, ...]:
        """Return the appointment types of the department, by name."""
        ...


class ScheduleDependents(Protocol):
    def for_room(self, room_id: Id) -> tuple[Dependent, ...]:
        """Return appointments and availability rules that use the room."""
        ...

    def for_appointment_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        """Return appointments and waitlist entries of the appointment type."""
        ...

    def for_clinician_profile(self, profile_id: Id) -> tuple[Dependent, ...]:
        """Return the appointments of the clinician holding the profile."""
        ...


class ClinicianProfiles(Protocol):
    def get(self, profile_id: Id) -> ClinicianProfile | None:
        """Return the profile, or None when absent."""
        ...

    def for_user(self, user_id: Id) -> ClinicianProfile | None:
        """Return the profile of the clinician user, or None."""
        ...

    def save(self, profile: ClinicianProfile) -> None:
        """Insert or replace the profile by id."""
        ...

    def delete(self, profile_id: Id) -> None:
        """Remove the profile; callers check its dependents first."""
        ...

    def matching(
        self,
        *,
        department_id: Id | None = None,
        specialty_id: Id | None = None,
        default_room_id: Id | None = None,
    ) -> tuple[ClinicianProfile, ...]:
        """Return the profiles matching every given criterion, by title."""
        ...


class SlotRefresh(Protocol):
    def refresh(self, profile_ids: tuple[Id, ...]) -> None:
        """Rebuild the profiles' stored slots in the caller's unit; a deleted profile keeps none."""
        ...


@dataclass(frozen=True, slots=True)
class Clinician:
    user_id: Id
    full_name: str


class StaffDirectory(Protocol):
    def active_clinician(self, user_id: Id) -> Clinician | None:
        """Return the user when it is an active clinician, else None."""
        ...
