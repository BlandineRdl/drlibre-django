import dataclasses
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
    DjangoSpecialties,
)
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_scheduling import rule as a_rule
from tests.fakes.world import FakeWorld


@dataclass(frozen=True, slots=True)
class Repos:
    """Where a scene is saved: the fake world's repositories or the Django ones."""

    hospitals: Any
    departments: Any
    rooms: Any
    types: Any
    specialties: Any
    profiles: Any
    users: Any
    rules: Any
    time_offs: Any


def django_repos() -> Repos:
    return Repos(
        DjangoHospitals(),
        DjangoDepartments(),
        DjangoRooms(),
        DjangoAppointmentTypes(),
        DjangoSpecialties(),
        DjangoClinicianProfiles(),
        DjangoUsers(),
        DjangoAvailabilityRules(),
        DjangoTimeOffs(),
    )


def world_repos(world: FakeWorld) -> Repos:
    return Repos(
        world.hospitals,
        world.departments,
        world.rooms,
        world.appointment_types,
        world.specialties,
        world.profiles,
        world.users,
        world.availability_rules,
        world.time_offs,
    )


@dataclass(frozen=True, slots=True)
class Directory:
    """Lille and Paris active, Roubaix closed near Lille; one active and one former clinician."""

    lille: Hospital
    paris: Hospital
    roubaix: Hospital
    cardiology: Department
    room: Room
    online: AppointmentType
    offline: AppointmentType
    specialty: Specialty
    retired: Specialty
    clinician: User
    profile: ClinicianProfile
    former: User
    former_profile: ClinicianProfile
    admin: User
    rule: AvailabilityRule
    time_off: TimeOff

    def ids(self) -> dict[str, str]:
        """Each record's id by field name, for paths such as `/fhir/Organization/$lille`."""
        return {f.name: str(getattr(self, f.name).id) for f in dataclasses.fields(self)}


def _hospital(name: str, city: str, latitude: float, longitude: float, active: bool) -> Hospital:
    found = build.hospital(name=name)
    return dataclasses.replace(
        found, city=city, latitude=latitude, longitude=longitude, active=active
    )


def _user(role: Role, name: str, *, active: bool = True) -> User:
    return User(
        id=Id(),
        email=Email(f"{name.lower().replace(' ', '.')}.{Id().value.hex[:6]}@example.org"),
        full_name=name,
        role=role,
        active=active,
        password_hash=None,
        must_change_password=False,
        last_login_at=None,
        created_at=build.AT,
        updated_at=build.AT,
        phone="+33 6 00 00 00 00",
    )


def _profile(
    user: User, department: Department, specialty: Specialty, **fields: str
) -> ClinicianProfile:
    raw = {
        "department_id": str(department.id),
        "specialty_id": str(specialty.id),
        "title": "Dr",
        "bio": "Cardiologue",
        "weight": "3",
        **fields,
    }
    return ClinicianProfile.attach(raw, user_id=user.id, at=build.AT)


def a_directory(repos: Repos) -> Directory:
    lille = _hospital("Hôpital Nord", "Lille", 50.63, 3.06, True)
    paris = _hospital("Hôpital Sud", "Paris", 48.85, 2.35, True)
    roubaix = _hospital("Hôpital Fermé", "Roubaix", 50.66, 3.1, False)
    for h in (lille, paris, roubaix):
        repos.hospitals.save(h)
    cardiology = build.department(lille.id)
    repos.departments.save(cardiology)
    room = build.room(cardiology.id)
    repos.rooms.save(room)
    online = dataclasses.replace(
        build.appointment_type(cardiology.id), name="Consultation", bookable_online=True
    )
    offline = dataclasses.replace(
        build.appointment_type(cardiology.id), name="Échographie", bookable_online=False
    )
    for t in (online, offline):
        repos.types.save(t)
    specialty = build.specialty()
    retired = dataclasses.replace(build.specialty(), name="Ancienne", active=False)
    for s in (specialty, retired):
        repos.specialties.save(s)
    clinician = _user(Role.CLINICIAN, "Alice Martin")
    former = _user(Role.CLINICIAN, "Bruno Petit", active=False)
    admin = _user(Role.ADMIN, "Admin Central")
    for u in (clinician, former, admin):
        repos.users.save(u)
    profile = _profile(clinician, cardiology, specialty, default_room_id=str(room.id))
    former_profile = _profile(former, cardiology, specialty)
    for p in (profile, former_profile):
        repos.profiles.save(p)
    rule = a_rule(
        profile.id,
        weekday=1,
        start=time(9),
        end=time(12),
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        room_id=room.id,
    )
    repos.rules.save(rule)
    repos.rules.save(a_rule(former_profile.id, weekday=2))
    time_off = TimeOff(
        id=Id(),
        clinician_id=profile.id,
        start=datetime(2026, 12, 24, 8, tzinfo=UTC),
        end=datetime(2026, 12, 26, 18, tzinfo=UTC),
        reason="Congés",
    )
    repos.time_offs.save(time_off)
    return Directory(
        lille, paris, roubaix, cardiology, room, online, offline, specialty, retired,
        clinician, profile, former, former_profile, admin, rule, time_off,
    )  # fmt: skip
