import pytest

from drlibre.identity.application.ports.outbound import StaffProfiles
from drlibre.identity.infrastructure.staff_profiles import OrganisationStaffProfiles
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.organisation.infrastructure.repositories import (
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoHospitals,
    DjangoSpecialties,
)
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.fakes.staff_profiles import InMemoryStaffProfiles

REAL = [pytest.mark.integration, pytest.mark.django_db]


def stored_profile(user_id: Id) -> ClinicianProfile:
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    specialty = build.specialty()
    DjangoSpecialties().save(specialty)
    fields = {
        "department_id": str(department.id),
        "specialty_id": str(specialty.id),
        "title": "Dr X",
    }
    profile = ClinicianProfile.attach(fields, user_id=user_id, at=build.AT)
    DjangoClinicianProfiles().save(profile)
    return profile


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="organisation", marks=REAL),
    ]
)
def profiles(request: pytest.FixtureRequest) -> tuple[StaffProfiles, Id, Id]:
    """Staff profiles knowing one clinician with a profile (first id) and one without."""
    holder, other = Id(), Id()
    if request.param == "fake":
        fake = InMemoryStaffProfiles()
        fake.profiles[holder] = Dependent("clinician", Id(), "Dr X")
        return fake, holder, other
    stored_profile(holder)
    return OrganisationStaffProfiles(DjangoReferenceQueries()), holder, other


def test_a_clinician_profile_is_seen_as_a_dependent_of_its_user(
    profiles: tuple[StaffProfiles, Id, Id],
) -> None:
    """Règle §3.2 : supprimer le compte d'un praticien rattaché est refusé."""
    staff, holder, other = profiles

    found = staff.profile_of(holder)

    assert found is not None
    assert (found.kind, found.label) == ("clinician", "Dr X")
    assert staff.profile_of(other) is None
