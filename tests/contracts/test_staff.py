import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from drlibre.booking.application.ports.outbound import Patients, Staff
from drlibre.booking.infrastructure.identity_staff import IdentityStaff
from drlibre.booking.infrastructure.patients import IdentityPatients
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_booking import patient_user
from tests.fakes.booking import InMemoryPatients, InMemoryStaff
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Scene:
    staff: Staff
    patients: Patients
    add: Callable[..., User]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        users = InMemoryUsers()

        def add_fake(role: Role, *, active: bool = True) -> User:
            email = f"{role.value.lower()}-{Id()}@example.org"
            user = patient_user(Id(), email=email, role=role, active=active)
            users.save(user)
            return user

        return Scene(InMemoryStaff(users), InMemoryPatients(users), add_fake)

    def add_real(role: Role, *, active: bool = True) -> User:
        user = dataclasses.replace(stored_user(role), active=active)
        DjangoUsers().save(user)
        return user

    queries = DjangoUserQueries()
    return Scene(IdentityStaff(queries), IdentityPatients(queries), add_real)


@pytest.mark.parametrize(
    ("role", "active", "admin"),
    [(Role.ADMIN, True, True), (Role.ADMIN, False, False), (Role.CLINICIAN, True, False)],
)
def test_only_an_active_admin_counts_as_admin(
    scene: Scene, role: Role, active: bool, admin: bool
) -> None:
    """Story inscription par l'admin : seul un admin actif nomme un autre patient."""
    assert scene.staff.is_admin(scene.add(role, active=active).id) is admin
    assert not scene.staff.is_admin(Id())


def test_an_active_patient_is_found_by_email_whatever_its_case(scene: Scene) -> None:
    """Story inscription par l'admin : l'admin choisit un patient actif par son email."""
    patient = scene.add(Role.PATIENT)
    typed = f"  {patient.email.value.upper()} "

    assert scene.patients.active_patient_by_email(typed) == patient.id


@pytest.mark.parametrize(("role", "active"), [(Role.PATIENT, False), (Role.CLINICIAN, True)])
def test_an_inactive_patient_or_a_staff_email_finds_no_patient(
    scene: Scene, role: Role, active: bool
) -> None:
    user = scene.add(role, active=active)
    assert scene.patients.active_patient_by_email(user.email.value) is None
    assert scene.patients.active_patient_by_email("nobody@example.org") is None
