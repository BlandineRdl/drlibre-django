import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.reporting.application.ports.outbound import Admins
from drlibre.reporting.infrastructure.identity_admins import IdentityAdmins
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_booking import patient_user
from tests.fakes.reporting import InMemoryAdmins
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Scene:
    admins: Admins
    add: Callable[[Role, bool], User]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        users = InMemoryUsers()

        def add_fake(role: Role, active: bool) -> User:
            email = f"{role.value.lower()}-{Id()}@example.org"
            user = patient_user(Id(), email=email, role=role, active=active)
            users.save(user)
            return user

        return Scene(InMemoryAdmins(users), add_fake)

    def add_real(role: Role, active: bool) -> User:
        user = dataclasses.replace(stored_user(role), active=active)
        DjangoUsers().save(user)
        return user

    return Scene(IdentityAdmins(DjangoUserQueries()), add_real)


@pytest.mark.parametrize(
    ("role", "active", "admin"),
    [(Role.ADMIN, True, True), (Role.ADMIN, False, False), (Role.CLINICIAN, True, False)],
)
def test_only_an_active_admin_sees_the_dashboard(
    scene: Scene, role: Role, active: bool, admin: bool
) -> None:
    """Spec 10: the dashboard is the admin's."""
    assert scene.admins.is_admin(scene.add(role, active).id) is admin
    assert not scene.admins.is_admin(Id())
