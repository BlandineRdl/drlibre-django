import dataclasses
from dataclasses import dataclass

import pytest

from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.organisation.application.ports.outbound import (
    Clinician,
    ClinicianProfiles,
    Departments,
    Hospitals,
    Rooms,
    Specialties,
    StaffDirectory,
)
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.infrastructure.repositories import (
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
    DjangoSpecialties,
)
from drlibre.organisation.infrastructure.staff_directory import IdentityStaffDirectory
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.fakes.organisation import (
    InMemoryClinicianProfiles,
    InMemoryDepartments,
    InMemoryHospitals,
    InMemoryRooms,
    InMemorySpecialties,
)
from tests.fakes.staff_directory import InMemoryStaffDirectory

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Stores:
    profiles: ClinicianProfiles
    hospitals: Hospitals
    departments: Departments
    specialties: Specialties
    rooms: Rooms


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def stores(request: pytest.FixtureRequest) -> Stores:
    if request.param == "fake":
        return Stores(
            InMemoryClinicianProfiles(),
            InMemoryHospitals(),
            InMemoryDepartments(),
            InMemorySpecialties(),
            InMemoryRooms(),
        )
    return Stores(
        DjangoClinicianProfiles(),
        DjangoHospitals(),
        DjangoDepartments(),
        DjangoSpecialties(),
        DjangoRooms(),
    )


def a_profile(stores: Stores) -> ClinicianProfile:
    hospital = build.hospital()
    stores.hospitals.save(hospital)
    department = build.department(hospital.id)
    stores.departments.save(department)
    specialty = build.specialty()
    stores.specialties.save(specialty)
    room = build.room(department.id)
    stores.rooms.save(room)
    fields = {
        "department_id": str(department.id),
        "specialty_id": str(specialty.id),
        "default_room_id": str(room.id),
        "title": "Dr Ana Bel",
    }
    return ClinicianProfile.attach(fields, user_id=Id(), at=build.AT)


def test_a_profile_is_found_by_id_and_by_its_clinician(stores: Stores) -> None:
    profile = a_profile(stores)
    stores.profiles.save(profile)

    assert stores.profiles.get(profile.id) == profile
    assert stores.profiles.for_user(profile.user_id) == profile
    assert stores.profiles.for_user(Id()) is None
    assert profile.weight == 1


def test_a_deleted_profile_is_gone(stores: Stores) -> None:
    """Règle §10 : un profil praticien sans rendez-vous est supprimé."""
    profile = a_profile(stores)
    stores.profiles.save(profile)

    stores.profiles.delete(profile.id)

    assert stores.profiles.get(profile.id) is None
    assert stores.profiles.for_user(profile.user_id) is None


def test_profiles_are_matched_by_department_specialty_and_default_room(stores: Stores) -> None:
    profile = a_profile(stores)
    stores.profiles.save(dataclasses.replace(profile, weight=3))
    stored = dataclasses.replace(profile, weight=3)

    assert stores.profiles.matching(department_id=profile.department_id) == (stored,)
    assert stores.profiles.matching(specialty_id=profile.specialty_id) == (stored,)
    assert stores.profiles.matching(default_room_id=profile.default_room_id) == (stored,)
    assert stores.profiles.matching(department_id=Id()) == ()


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="identity", marks=REAL)]
)
def directory(request: pytest.FixtureRequest) -> tuple[StaffDirectory, Id, Id, Id]:
    """A directory knowing one active clinician, one inactive clinician and one admin."""
    if request.param == "fake":
        fake = InMemoryStaffDirectory()
        active = Id()
        fake.active_clinicians[active] = Clinician(active, "Demo Clinician")
        return fake, active, Id(), Id()
    active = stored_user(Role.CLINICIAN).id
    inactive = stored_user(Role.CLINICIAN, active=False).id
    admin = stored_user(Role.ADMIN).id
    return IdentityStaffDirectory(lookup=DjangoUserQueries()), active, inactive, admin


def test_only_active_clinicians_can_receive_a_profile(
    directory: tuple[StaffDirectory, Id, Id, Id],
) -> None:
    staff, active, inactive, admin = directory

    found = staff.active_clinician(active)

    assert found is not None
    assert found.user_id == active
    assert staff.active_clinician(inactive) is None
    assert staff.active_clinician(admin) is None
