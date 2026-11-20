from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

__all__ = [
    "AppointmentType",
    "AttachClinicianProfile",
    "ClinicianProfile",
    "DeleteAppointmentType",
    "DeleteDepartment",
    "DeleteHospital",
    "DeleteRecord",
    "DeleteRoom",
    "DeleteSpecialty",
    "Department",
    "EditClinicianProfile",
    "Hospital",
    "Option",
    "ReferenceQueries",
    "Room",
    "SaveAppointmentType",
    "SaveDepartment",
    "SaveHospital",
    "SaveRecord",
    "SaveRoom",
    "SaveSpecialty",
    "Specialty",
]


class SaveRecord(Protocol):
    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        """Create (no id) or update a record from raw form text; invalid_input or not_found."""
        ...


class DeleteRecord(Protocol):
    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        """Delete the record; not_found, or has_dependents listing what still uses it."""
        ...


class SaveHospital(SaveRecord, Protocol): ...


class SaveSpecialty(SaveRecord, Protocol): ...


class SaveDepartment(SaveRecord, Protocol): ...


class SaveRoom(SaveRecord, Protocol): ...


class SaveAppointmentType(SaveRecord, Protocol): ...


class DeleteHospital(DeleteRecord, Protocol): ...


class DeleteSpecialty(DeleteRecord, Protocol): ...


class DeleteDepartment(DeleteRecord, Protocol): ...


class DeleteRoom(DeleteRecord, Protocol): ...


class DeleteAppointmentType(DeleteRecord, Protocol): ...


class AttachClinicianProfile(Protocol):
    def execute(self, *, actor: Id | None, user_id: str, fields: Mapping[str, str]) -> Id:
        """Attach a profile to an active clinician who has none; invalid_input otherwise."""
        ...


class EditClinicianProfile(Protocol):
    def execute(self, *, actor: Id | None, profile_id: Id, fields: Mapping[str, str]) -> None:
        """Edit a profile from raw form text; not_found or invalid_input."""
        ...


@dataclass(frozen=True, slots=True)
class Option:
    id: Id
    label: str


class ReferenceQueries(Protocol):
    def hospitals(self, request: PageRequest) -> Page[Hospital]:
        """Hospitals matching the search on name or code, 20 per page, by name."""
        ...

    def specialties(self, request: PageRequest) -> Page[Specialty]:
        """Specialties matching the search on name or code, 20 per page, by name."""
        ...

    def departments(self, request: PageRequest) -> Page[Department]:
        """Departments matching the search on name or code, 20 per page, by name."""
        ...

    def rooms(self, request: PageRequest) -> Page[Room]:
        """Rooms matching the search on name or code, 20 per page, by name."""
        ...

    def appointment_types(self, request: PageRequest) -> Page[AppointmentType]:
        """Appointment types matching the search on name or code, 20 per page, by name."""
        ...

    def hospital(self, record_id: Id) -> Hospital | None:
        """One hospital, active or not, or None."""
        ...

    def specialty(self, record_id: Id) -> Specialty | None:
        """One specialty, active or not, or None."""
        ...

    def department(self, record_id: Id) -> Department | None:
        """One department, or None."""
        ...

    def room(self, record_id: Id) -> Room | None:
        """One room, active or not, or None."""
        ...

    def appointment_type(self, record_id: Id) -> AppointmentType | None:
        """One appointment type, active or not, or None."""
        ...

    def hospital_options(self) -> tuple[Option, ...]:
        """Every hospital as an option, by name."""
        ...

    def specialty_options(self) -> tuple[Option, ...]:
        """Every specialty as an option, by name."""
        ...

    def department_options(self) -> tuple[Option, ...]:
        """Every department as an option labelled with its hospital, by name."""
        ...

    def room_options(self) -> tuple[Option, ...]:
        """Every active room as an option labelled with its department, by name."""
        ...

    def clinician_profiles(self, request: PageRequest) -> Page[ClinicianProfile]:
        """Profiles matching the search on title, 20 per page, by title."""
        ...

    def clinician_profile(self, profile_id: Id) -> ClinicianProfile | None:
        """One profile, or None."""
        ...

    def profiled_user_ids(self) -> frozenset[Id]:
        """Users who already have a clinician profile."""
        ...
