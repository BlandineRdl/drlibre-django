from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.identity.domain.user import Email, Role, User
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.fakes.world import FakeWorld

scenarios("../../features/identity/manage_users.feature")

TEMPORARY = "temporary-pass-1"


class Outcome:
    def __init__(self) -> None:
        self.error: DomainError | None = None
        self.tokens: dict[str, str] = {}
        self.mark = 0


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


@pytest.fixture
def admin(world: FakeWorld) -> User:
    user_id = world.app.save_user.execute(
        actor=None,
        user_id=None,
        full_name="Admin",
        email="admin@example.org",
        role="ADMIN",
        active=True,
        temporary_password=TEMPORARY,
    )
    user = world.users.get(user_id)
    assert user is not None
    return user


def user_of(world: FakeWorld, email: str) -> User:
    user = world.users.by_email(Email.parse(email))
    assert user is not None
    return user


def write(world: FakeWorld, outcome: Outcome, action: Callable[[], object]) -> None:
    outcome.mark = len(world.audit.entries)
    try:
        action()
        outcome.error = None
    except DomainError as error:
        outcome.error = error


def edit(
    world: FakeWorld,
    admin: User,
    user: User,
    *,
    full_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    active: bool | None = None,
) -> None:
    world.app.save_user.execute(
        actor=admin.id,
        user_id=user.id,
        full_name=user.full_name if full_name is None else full_name,
        email=user.email.value if email is None else email,
        role=user.role.value if role is None else role,
        active=user.active if active is None else active,
        temporary_password="",
    )


def changes(field: str, value: str) -> dict[str, Any]:
    return {field: value == "true"} if field == "active" else {field: value}


@given(parsers.parse('the signed-in admin "{email}"'))
def signed_in_admin(admin: User) -> None:
    assert admin.role is Role.ADMIN


@given(parsers.parse('a {role} account "{email}"'))
def account(world: FakeWorld, admin: User, role: str, email: str) -> None:
    world.app.save_user.execute(
        actor=admin.id,
        user_id=None,
        full_name="Someone",
        email=email,
        role=role,
        active=True,
        temporary_password=TEMPORARY,
    )


@given(parsers.parse('a {role} account named "{name}" with email "{email}"'))
def named_account(world: FakeWorld, admin: User, role: str, name: str, email: str) -> None:
    world.app.save_user.execute(
        actor=admin.id,
        user_id=None,
        full_name=name,
        email=email,
        role=role,
        active=True,
        temporary_password=TEMPORARY,
    )


@given(parsers.parse('a {role} account "{email}" that is signed in'))
def signed_in_account(
    world: FakeWorld, outcome: Outcome, admin: User, role: str, email: str
) -> None:
    account(world, admin, role, email)
    signed = world.app.sign_in.execute(
        email=email, password=TEMPORARY, user_agent="pytest", network="192.0.2.1"
    )
    outcome.tokens[email] = signed.token


@given(parsers.parse('"{email}" has an {state} appointment in {days:d} days'))
@given(parsers.parse('"{email}" has a {state} appointment in {days:d} days'))
def has_appointment(world: FakeWorld, email: str, state: str, days: int) -> None:
    start = world.clock.now() + timedelta(days=days)
    dependent = Dependent("appointment", Id(), f"RDV {start:%Y-%m-%d}")
    world.appointments.rows.append(
        (user_of(world, email).id, Id(), start, state == "active", dependent)
    )


@when(
    parsers.parse(
        'the admin creates the {role} "{name}" with email "{email}" and password "{password}"'
    )
)
def creates(
    world: FakeWorld, outcome: Outcome, admin: User, role: str, name: str, email: str, password: str
) -> None:
    write(
        world,
        outcome,
        lambda: world.app.save_user.execute(
            actor=admin.id,
            user_id=None,
            full_name=name,
            email=email,
            role=role,
            active=True,
            temporary_password=password,
        ),
    )


@when(parsers.parse('the admin edits their own account setting {field} "{value}"'))
def edits_own(world: FakeWorld, outcome: Outcome, admin: User, field: str, value: str) -> None:
    write(world, outcome, lambda: edit(world, admin, admin, **changes(field, value)))


@when(parsers.parse('the admin edits "{email}" setting {field} "{value}"'))
def edits(
    world: FakeWorld, outcome: Outcome, admin: User, email: str, field: str, value: str
) -> None:
    user = user_of(world, email)
    write(world, outcome, lambda: edit(world, admin, user, **changes(field, value)))


@when(
    parsers.parse(
        'the admin renames "{email}" to "{name}" with email "{new_email}", '
        'role "{role}" and active "{active}"'
    )
)
def renames(
    world: FakeWorld,
    outcome: Outcome,
    admin: User,
    email: str,
    name: str,
    new_email: str,
    role: str,
    active: str,
) -> None:
    user = user_of(world, email)
    write(
        world,
        outcome,
        lambda: edit(
            world, admin, user, full_name=name, email=new_email, role=role, active=active == "true"
        ),
    )


@when(parsers.parse('the admin searches users for "{text}"'), target_fixture="found")
def searches(world: FakeWorld, text: str) -> list[str]:
    page = world.app.user_queries.users(PageRequest(search=text))
    return [u.email.value for u in page.items]


@then(parsers.parse('the users found are "{emails}"'))
def users_found(found: list[str], emails: str) -> None:
    assert found == emails.split(",")


@then(parsers.parse('the user "{email}" is the {role} "{name}", inactive'))
def user_is(world: FakeWorld, email: str, role: str, name: str) -> None:
    user = user_of(world, email)
    assert (user.role, user.full_name, user.active) == (Role(role), name, False)


@when(parsers.parse('the admin deletes "{email}"'))
def deletes(world: FakeWorld, outcome: Outcome, admin: User, email: str) -> None:
    target = user_of(world, email)
    write(world, outcome, lambda: world.app.delete_user.execute(actor=admin.id, user_id=target.id))


@then(parsers.parse('the user "{email}" exists and must change password'))
def exists_forced(world: FakeWorld, email: str) -> None:
    user = world.users.by_email(Email(email))
    assert user is not None
    assert user.email.value == email
    assert user.must_change_password is True
    assert user.password_hash == world.hasher.hash(TEMPORARY)


@then(parsers.parse('the audit holds "{action}" with only "{keys}"'))
def audited_keys(world: FakeWorld, outcome: Outcome, action: str, keys: str) -> None:
    [entry] = world.audit.entries[outcome.mark :]
    assert entry.action == action
    assert [k for k, _ in entry.metadata] == keys.split(",")


@then(parsers.parse('the audit holds "{action}" changing "{fields}"'))
def audited_changes(world: FakeWorld, outcome: Outcome, action: str, fields: str) -> None:
    [entry] = world.audit.entries[outcome.mark :]
    assert entry.action == action
    assert dict(entry.metadata)["changed"] == tuple(fields.split(","))


@then(parsers.parse('the audit holds "{action}" closing {count:d} session'))
def audited_closing(world: FakeWorld, outcome: Outcome, action: str, count: int) -> None:
    [entry] = world.audit.entries[outcome.mark :]
    assert entry.action == action
    assert dict(entry.metadata)["sessions_closed"] == count


@then(parsers.parse('the write is refused as invalid on "{field}"'))
def invalid_on(outcome: Outcome, field: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == "invalid_input"
    assert [f["field"] for f in outcome.error.details["fields"]] == [field]


@then(parsers.parse('the write is refused as "{code}" inviting to deactivate'))
def refused_deactivate(world: FakeWorld, outcome: Outcome, code: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == code
    assert "Désactivez ce compte" in outcome.error.message
    assert world.audit.entries[outcome.mark :] == []


@then(parsers.parse("the write is refused listing {count:d} appointment"))
def refused_listing(outcome: Outcome, count: int) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == "has_dependents"
    assert [d["kind"] for d in outcome.error.details["dependents"]] == ["appointment"] * count


@then(parsers.parse('the session of "{email}" no longer identifies anyone'))
def session_closed(world: FakeWorld, outcome: Outcome, email: str) -> None:
    assert world.app.authenticate_session.execute(token=outcome.tokens[email]) is None
    assert all(s.user_id != user_of(world, email).id for s in world.sessions.rows.values())


@then(parsers.parse('no user "{email}" exists'))
def no_user(world: FakeWorld, email: str) -> None:
    assert world.users.by_email(Email(email)) is None


@given(parsers.parse('"{email}" has a clinician profile'))
def has_clinician_profile(world: FakeWorld, email: str) -> None:
    world.staff_profiles.profiles[user_of(world, email).id] = Dependent("clinician", Id(), "Dr Ana")
