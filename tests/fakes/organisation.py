from typing import Protocol

from drlibre.organisation.application.ports.inbound import Option, ReferenceQueries
from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    ClinicianProfiles,
    Departments,
    Hospitals,
    Rooms,
    ScheduleDependents,
    Specialties,
)
from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest


class Named(Protocol):
    @property
    def id(self) -> Id: ...

    @property
    def code(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def label(self) -> str: ...


class InMemoryRecords[T: Named]:
    def __init__(self) -> None:
        self.rows: dict[Id, T] = {}

    def get(self, record_id: Id) -> T | None:
        return self.rows.get(record_id)

    def save(self, record: T) -> None:
        self.rows[record.id] = record

    def delete(self, record_id: Id) -> None:
        self.rows.pop(record_id, None)

    def code_taken(self, code: str, *, except_id: Id) -> bool:
        return any(r.code == code and r.id != except_id for r in self.rows.values())

    def where(self, **match: object) -> tuple[T, ...]:
        found = [r for r in self.rows.values() if all(getattr(r, k) == v for k, v in match.items())]
        return tuple(sorted(found, key=lambda r: (r.name, r.code)))


class InMemoryHospitals(InMemoryRecords[Hospital], Hospitals):
    pass


class InMemorySpecialties(InMemoryRecords[Specialty], Specialties):
    pass


class InMemoryDepartments(InMemoryRecords[Department], Departments):
    def for_hospital(self, hospital_id: Id) -> tuple[Department, ...]:
        return self.where(hospital_id=hospital_id)


class InMemoryRooms(InMemoryRecords[Room], Rooms):
    def for_department(self, department_id: Id) -> tuple[Room, ...]:
        return self.where(department_id=department_id)


class InMemoryAppointmentTypes(InMemoryRecords[AppointmentType], AppointmentTypes):
    def for_department(self, department_id: Id) -> tuple[AppointmentType, ...]:
        return self.where(department_id=department_id)


class InMemoryScheduleDependents(ScheduleDependents):
    def __init__(self) -> None:
        self.by_room: dict[Id, tuple[Dependent, ...]] = {}
        self.by_appointment_type: dict[Id, tuple[Dependent, ...]] = {}
        self.by_clinician_profile: dict[Id, tuple[Dependent, ...]] = {}

    def for_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return self.by_room.get(room_id, ())

    def for_appointment_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return self.by_appointment_type.get(appointment_type_id, ())

    def for_clinician_profile(self, profile_id: Id) -> tuple[Dependent, ...]:
        return self.by_clinician_profile.get(profile_id, ())


def _page[T: Named](records: InMemoryRecords[T], request: PageRequest) -> Page[T]:
    needle = request.search.lower()
    found = [r for r in records.where() if needle in r.name.lower() or needle in r.code.lower()]
    window = tuple(found[request.offset : request.offset + PAGE_SIZE])
    return Page(window, len(found), request.number)


def _options[T: Named](records: InMemoryRecords[T]) -> tuple[Option, ...]:
    return tuple(Option(r.id, r.label) for r in records.where())


class InMemoryReferenceQueries(ReferenceQueries):
    """Reads straight from the in-memory repositories."""

    def __init__(
        self,
        *,
        hospitals: InMemoryHospitals,
        specialties: InMemorySpecialties,
        departments: InMemoryDepartments,
        rooms: InMemoryRooms,
        appointment_types: InMemoryAppointmentTypes,
        profiles: "InMemoryClinicianProfiles",
    ) -> None:
        self.stores = (hospitals, specialties, departments, rooms, appointment_types)
        self.profiles = profiles

    def hospitals(self, request: PageRequest) -> Page[Hospital]:
        return _page(self.stores[0], request)

    def specialties(self, request: PageRequest) -> Page[Specialty]:
        return _page(self.stores[1], request)

    def departments(self, request: PageRequest) -> Page[Department]:
        return _page(self.stores[2], request)

    def rooms(self, request: PageRequest) -> Page[Room]:
        return _page(self.stores[3], request)

    def appointment_types(self, request: PageRequest) -> Page[AppointmentType]:
        return _page(self.stores[4], request)

    def hospital(self, record_id: Id) -> Hospital | None:
        return self.stores[0].get(record_id)

    def specialty(self, record_id: Id) -> Specialty | None:
        return self.stores[1].get(record_id)

    def department(self, record_id: Id) -> Department | None:
        return self.stores[2].get(record_id)

    def room(self, record_id: Id) -> Room | None:
        return self.stores[3].get(record_id)

    def appointment_type(self, record_id: Id) -> AppointmentType | None:
        return self.stores[4].get(record_id)

    def hospital_options(self) -> tuple[Option, ...]:
        return _options(self.stores[0])

    def specialty_options(self) -> tuple[Option, ...]:
        return _options(self.stores[1])

    def department_options(self) -> tuple[Option, ...]:
        return _options(self.stores[2])

    def room_options(self) -> tuple[Option, ...]:
        rooms = self.stores[3]
        return tuple(Option(r.id, r.label) for r in rooms.where() if r.active)

    def clinician_profiles(
        self, request: PageRequest, *, named: frozenset[Id] = frozenset()
    ) -> Page[ClinicianProfile]:
        needle = request.search.lower()
        found = [
            p for p in self.profiles.matching() if needle in p.title.lower() or p.user_id in named
        ]
        window = tuple(found[request.offset : request.offset + PAGE_SIZE])
        return Page(window, len(found), request.number)

    def clinician_profile(self, profile_id: Id) -> ClinicianProfile | None:
        return self.profiles.get(profile_id)

    def clinician_profile_of(self, user_id: Id) -> ClinicianProfile | None:
        return self.profiles.for_user(user_id)

    def profiled_user_ids(self) -> frozenset[Id]:
        return frozenset(p.user_id for p in self.profiles.rows.values())


class InMemoryClinicianProfiles(ClinicianProfiles):
    def __init__(self) -> None:
        self.rows: dict[Id, ClinicianProfile] = {}

    def get(self, profile_id: Id) -> ClinicianProfile | None:
        return self.rows.get(profile_id)

    def for_user(self, user_id: Id) -> ClinicianProfile | None:
        return next((p for p in self.rows.values() if p.user_id == user_id), None)

    def save(self, profile: ClinicianProfile) -> None:
        self.rows[profile.id] = profile

    def delete(self, profile_id: Id) -> None:
        self.rows.pop(profile_id, None)

    def matching(
        self,
        *,
        department_id: Id | None = None,
        specialty_id: Id | None = None,
        default_room_id: Id | None = None,
    ) -> tuple[ClinicianProfile, ...]:
        wanted = {
            "department_id": department_id,
            "specialty_id": specialty_id,
            "default_room_id": default_room_id,
        }
        found = [
            p
            for p in self.rows.values()
            if all(getattr(p, k) == v for k, v in wanted.items() if v is not None)
        ]
        return tuple(sorted(found, key=lambda p: p.title))
