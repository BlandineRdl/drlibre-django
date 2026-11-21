import dataclasses

from django.conf import settings
from django.test import Client

from drlibre.identity.domain.user import Email, Role, User
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.scheduling.application.ports.outbound import Clinician
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.fakes.world import FakeWorld

PASSWORD = "fake-password-1"


def fake_user(world: FakeWorld, *, user_id: Id, role: Role, name: str) -> User:
    at = world.clock.now()
    user = User(
        id=user_id,
        email=Email(f"{user_id.value.hex[:12]}@example.org"),
        full_name=name,
        role=role,
        active=True,
        password_hash=world.hasher.hash(PASSWORD),
        must_change_password=False,
        last_login_at=None,
        created_at=at,
        updated_at=at,
    )
    world.users.save(user)
    return user


def signed_in(world: FakeWorld, user: User) -> Client:
    """The real web views over the fake wiring, for a user holding a fake session."""
    signed = world.app.sign_in.execute(
        email=user.email.value, password=PASSWORD, user_agent="tests"
    )
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = signed.token
    return client


def fake_clinician(
    world: FakeWorld,
    *,
    user_id: Id,
    profile_id: Id,
    department_id: Id,
    time_zone: str,
    name: str,
) -> User:
    """One clinician seen alike by organisation (web reads) and scheduling (use cases)."""
    if world.departments.get(department_id) is None:
        hospital = dataclasses.replace(build.hospital(), time_zone=time_zone)
        world.hospitals.save(hospital)
        world.departments.save(dataclasses.replace(build.department(hospital.id), id=department_id))
    fields = {"department_id": str(department_id), "specialty_id": str(Id()), "title": name}
    profile = ClinicianProfile.attach(fields, user_id=user_id, at=world.clock.now())
    world.profiles.save(dataclasses.replace(profile, id=profile_id))
    world.scheduling_directory.clinicians[profile_id] = Clinician(
        profile_id, department_id, time_zone, active=True
    )
    world.scheduling_directory.profile_of_user[user_id] = profile_id
    return fake_user(world, user_id=user_id, role=Role.CLINICIAN, name=name)
