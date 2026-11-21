import inspect
from datetime import UTC, date, datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.identity.domain.user import Email, Role, User
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.fakes.world import FakeWorld

scenarios("../../features/identity/le_patient_met_a_jour_son_profil.feature")


class Profile:
    def __init__(self) -> None:
        self.user_id = Id()
        self.error: DomainError | None = None
        self.values: tuple[str, ...] = ()


@pytest.fixture
def profile() -> Profile:
    return Profile()


def typed(raw: str) -> str:
    return "" if raw == "none" else raw


def stored(world: FakeWorld, profile: Profile) -> User:
    return world.users.rows[profile.user_id]


@given(
    parsers.parse('a patient "{email}" named "{name}" with phone "{phone}" born on "{birth_date}"')
)
def patient(
    world: FakeWorld, profile: Profile, email: str, name: str, phone: str, birth_date: str
) -> None:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    world.users.save(
        User(
            id=profile.user_id,
            email=Email(email),
            full_name=name,
            role=Role.PATIENT,
            active=True,
            password_hash=None,
            must_change_password=False,
            last_login_at=None,
            created_at=at,
            updated_at=at,
            phone=phone,
            birth_date=date.fromisoformat(birth_date),
        )
    )
    profile.values = (phone, birth_date)


@when(parsers.parse('the patient saves the phone "{phone}" and the birth date "{birth_date}"'))
def saves(world: FakeWorld, profile: Profile, phone: str, birth_date: str) -> None:
    profile.values += (phone, birth_date)
    try:
        world.app.update_profile.execute(
            user_id=profile.user_id, phone=typed(phone), birth_date=typed(birth_date)
        )
    except DomainError as error:
        profile.error = error


@then(parsers.parse('the patient is still named "{name}" with email "{email}"'))
def same_identity(world: FakeWorld, profile: Profile, name: str, email: str) -> None:
    user = stored(world, profile)
    assert (user.full_name, user.email.value) == (name, email)


@then("the profile offers no way to change the name or the email")
def no_identity_fields() -> None:
    names = set(inspect.signature(FakeWorld().app.update_profile.execute).parameters)
    assert names == {"user_id", "phone", "birth_date"}


@then(parsers.parse('the patient has the phone "{phone}" and the birth date "{birth_date}"'))
def has_profile(world: FakeWorld, profile: Profile, phone: str, birth_date: str) -> None:
    user = stored(world, profile)
    expected_birth = None if birth_date == "none" else date.fromisoformat(birth_date)
    assert (user.phone, user.birth_date) == (typed(phone) or None, expected_birth)


@then(parsers.parse('the change is refused as invalid on "{field}" with its message'))
def refused_on(profile: Profile, field: str) -> None:
    assert profile.error is not None
    assert profile.error.code is ErrorCode.INVALID_INPUT
    (only,) = profile.error.details["fields"]
    assert only["field"] == field
    assert only["message"]


@then("nothing is audited")
def nothing_audited(world: FakeWorld) -> None:
    assert world.audit.entries == []


@then(
    parsers.parse(
        'the audit entry "{action}" by the patient names only the changed fields "{fields}"'
    )
)
def audit_names_fields(world: FakeWorld, profile: Profile, action: str, fields: str) -> None:
    (entry,) = world.audit.entries
    assert (entry.action, entry.actor) == (action, profile.user_id)
    assert dict(entry.metadata) == {"changed": tuple(f.strip() for f in fields.split(","))}


@then("no audit entry holds the old or new values")
def audit_without_values(world: FakeWorld, profile: Profile) -> None:
    text = repr(world.audit.entries)
    assert not [v for v in profile.values if v != "none" and v in text]
