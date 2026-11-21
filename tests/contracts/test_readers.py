import dataclasses
from collections.abc import Callable

import pytest

from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import Reader, ReaderKind, Readers
from drlibre.interop.infrastructure.sql_readers import SqlReaders
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_scheduling import stored_department, stored_profile
from tests.builders_web import fake_user
from tests.fakes.readers import InMemoryReaders
from tests.fakes.world import FakeWorld

REAL = [pytest.mark.integration, pytest.mark.django_db]

# Saves a user of the role, with a clinician profile when asked, and returns its id and profile.
type Scene = Callable[[Role, bool, bool], tuple[Id, Id | None]]


def fake_scene(world: FakeWorld) -> Scene:
    def add(role: Role, active: bool, with_profile: bool) -> tuple[Id, Id | None]:
        user = fake_user(world, user_id=Id(), role=role, name="Demo")
        world.users.save(dataclasses.replace(user, active=active))
        if not with_profile:
            return user.id, None
        fields = {"department_id": str(Id()), "specialty_id": str(Id()), "title": "Dr X"}
        profile = ClinicianProfile.attach(fields, user_id=user.id, at=build.AT)
        world.profiles.save(profile)
        return user.id, profile.id

    return add


def real_scene(role: Role, active: bool, with_profile: bool) -> tuple[Id, Id | None]:
    user = stored_user(role, active=active)
    if not with_profile:
        return user.id, None
    return user.id, stored_profile(stored_department(), user_id=user.id).id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def readers(request: pytest.FixtureRequest) -> tuple[Readers, Scene]:
    if request.param == "fake":
        world = FakeWorld()
        return InMemoryReaders(world.users, world.profiles), fake_scene(world)
    return SqlReaders(), real_scene


def test_no_user_reads_as_a_visitor(readers: tuple[Readers, Scene]) -> None:
    port, _ = readers

    assert port.of(None) == Reader.anonymous()


def test_a_clinician_profile_makes_a_clinician_reader(readers: tuple[Readers, Scene]) -> None:
    port, add = readers
    user_id, profile_id = add(Role.CLINICIAN, True, True)

    assert port.of(user_id) == Reader(ReaderKind.CLINICIAN, user_id, profile_id)


@pytest.mark.parametrize(
    ("role", "active", "kind"),
    [
        (Role.ADMIN, True, ReaderKind.ADMIN),
        (Role.ADMIN, False, ReaderKind.PATIENT),
        (Role.PATIENT, True, ReaderKind.PATIENT),
    ],
    ids=["active-admin", "inactive-admin", "patient"],
)
def test_an_active_admin_reads_as_admin_anyone_else_as_patient(
    readers: tuple[Readers, Scene], role: Role, active: bool, kind: ReaderKind
) -> None:
    port, add = readers
    user_id, _ = add(role, active, False)

    assert port.of(user_id) == Reader(kind, user_id)


def test_an_unknown_user_reads_as_patient(readers: tuple[Readers, Scene]) -> None:
    port, _ = readers
    user_id = Id()

    assert port.of(user_id) == Reader(ReaderKind.PATIENT, user_id)
