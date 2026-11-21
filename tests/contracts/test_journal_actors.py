import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from drlibre.audit.application.ports.outbound import JournalActors
from drlibre.audit.infrastructure.identity_actors import IdentityJournalActors
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_booking import patient_user
from tests.fakes.journal_actors import InMemoryJournalActors
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Scene:
    actors: JournalActors
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

        return Scene(InMemoryJournalActors(users), add_fake)

    def add_real(role: Role, *, active: bool = True) -> User:
        user = dataclasses.replace(stored_user(role), active=active)
        DjangoUsers().save(user)
        return user

    queries = DjangoUserQueries()
    return Scene(IdentityJournalActors(users=queries, staff=queries), add_real)


@pytest.mark.parametrize(
    ("role", "active", "admin"),
    [(Role.ADMIN, True, True), (Role.ADMIN, False, False), (Role.CLINICIAN, True, False)],
)
def test_only_an_active_admin_reads_the_journal(
    scene: Scene, role: Role, active: bool, admin: bool
) -> None:
    """Story journal d'audit : réservé à l'admin."""
    assert scene.actors.is_admin(scene.add(role, active=active).id) is admin
    assert not scene.actors.is_admin(Id())


def test_an_actor_is_found_by_email_whatever_its_case_active_or_not(scene: Scene) -> None:
    """Story journal d'audit : le filtre porte sur l'acteur."""
    user = scene.add(Role.PATIENT, active=False)
    assert scene.actors.id_of(f"  {user.email.value.upper()} ") == user.id
    assert scene.actors.id_of(f"nobody-{Id()}@example.org") is None


def test_each_known_actor_gets_its_email_and_unknown_ids_none(scene: Scene) -> None:
    """Story journal d'audit : chaque entrée montre l'acteur."""
    first, second = scene.add(Role.PATIENT), scene.add(Role.ADMIN, active=False)
    found = scene.actors.emails_of(frozenset({first.id, second.id, Id()}))
    assert found == {first.id: first.email.value, second.id: second.email.value}
