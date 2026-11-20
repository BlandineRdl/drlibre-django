import dataclasses
from datetime import timedelta

import pytest
from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import Container
from drlibre.identity.application.access import authorize_owned
from drlibre.identity.application.ports.inbound import Identity, SignedIn
from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import Email, Role, User
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.fakes.world import FakeWorld

scenarios(
    "../../features/identity/sign_in.feature",
    "../../features/identity/lockout.feature",
    "../../features/identity/change_password.feature",
    "../../features/identity/access.feature",
)


class Outcome:
    def __init__(self) -> None:
        self.signed_in: SignedIn | None = None
        self.token: str | None = None
        self.identity: Identity | None = None
        self.error: DomainError | None = None
        self.record: object | None = None
        self.status: int | None = None
        self.body: dict[str, object] = {}
        self.password = ""


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


@pytest.fixture
def web(fake_container: Container) -> Client:
    """A browser stand-in served by the real views over the fake wiring."""
    return Client()


def add_user(world: FakeWorld, email: str, role: str, password: str | None, **extra: bool) -> User:
    at = world.clock.now()
    user = User(
        id=Id(),
        email=Email.parse(email),
        full_name=f"User {role.title()}",
        role=Role(role),
        active=extra.get("active", True),
        password_hash=world.hasher.hash(password) if password else None,
        must_change_password=extra.get("must_change", False),
        last_login_at=None,
        created_at=at,
        updated_at=at,
    )
    world.users.save(user)
    return user


def user_of(world: FakeWorld, email: str) -> User:
    user = world.users.by_email(Email.parse(email))
    assert user is not None
    return user


@given(parsers.parse('an active {role} "{email}" with password "{password}"'))
def active_user(world: FakeWorld, role: str, email: str, password: str) -> None:
    add_user(world, email, role, password)


@given(parsers.parse('an inactive {role} "{email}" with password "{password}"'))
def inactive_user(world: FakeWorld, role: str, email: str, password: str) -> None:
    add_user(world, email, role, password, active=False)


@given(parsers.parse('a {role} "{email}" created by an admin with password "{password}"'))
def temporary_user(world: FakeWorld, role: str, email: str, password: str) -> None:
    add_user(world, email, role, password, must_change=True)


@given(parsers.parse('a passwordless {role} "{email}"'))
def passwordless_user(world: FakeWorld, role: str, email: str) -> None:
    add_user(world, email, role, None)


def attempt(world: FakeWorld, outcome: Outcome, email: str, password: str) -> None:
    world.hasher.verifications = 0
    world.audit.entries.clear()
    try:
        outcome.signed_in = world.app.sign_in.execute(
            email=email, password=password, user_agent="pytest"
        )
        outcome.token = outcome.signed_in.token
        outcome.error = None
    except DomainError as error:
        outcome.signed_in = None
        outcome.error = error


@given(parsers.parse('"{email}" signs in with "{password}"'))
@when(parsers.parse('"{email}" signs in with "{password}"'))
def signs_in(world: FakeWorld, outcome: Outcome, email: str, password: str) -> None:
    attempt(world, outcome, email, password)


@given(parsers.parse('"{email}" signed in'))
def signed_in(world: FakeWorld, outcome: Outcome, email: str) -> None:
    password = {"admin@example.org": "admin-password-1"}.get(email, "clinic-password-1")
    attempt(world, outcome, email, password)
    assert outcome.signed_in is not None


@given(parsers.parse('"{email}" failed to sign in {count:d} times in {minutes:d} minutes'))
def failed_many(world: FakeWorld, outcome: Outcome, email: str, count: int, minutes: int) -> None:
    step = timedelta(minutes=minutes) / count
    for _ in range(count):
        attempt(world, outcome, email, "not-the-password")
        world.clock.at += step


@when(parsers.parse("{amount:d} {unit} pass"))
def time_passes(world: FakeWorld, amount: int, unit: str) -> None:
    world.clock.at += timedelta(**{unit: amount})


@when("the session is used")
def session_used(world: FakeWorld, outcome: Outcome) -> None:
    assert outcome.token is not None
    outcome.identity = world.app.authenticate_session.execute(token=outcome.token)


@when(parsers.parse('"{email}" is deactivated'))
def deactivated(world: FakeWorld, email: str) -> None:
    user = user_of(world, email)
    world.users.save(dataclasses.replace(user, active=False))


@when("the session is signed out")
def signs_out(world: FakeWorld, outcome: Outcome) -> None:
    assert outcome.token is not None
    world.audit.entries.clear()
    world.app.sign_out.execute(token=outcome.token)


@when(parsers.parse('"{email}" changes password from "{current}" to "{new}"'))
def changes_password(
    world: FakeWorld, outcome: Outcome, email: str, current: str, new: str
) -> None:
    world.audit.entries.clear()
    try:
        world.app.change_password.execute(
            user_id=user_of(world, email).id, current_password=current, new_password=new
        )
    except DomainError as error:
        outcome.error = error


def identity_of(world: FakeWorld, email: str) -> Identity:
    user = user_of(world, email)
    return Identity(
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        has_password=user.has_password,
        must_change_password=False,
        session_expires_at=world.clock.now(),
        session_renewed=False,
    )


def open_record(outcome: Outcome, record: object | None, owner: Id | None, who: Identity) -> None:
    try:
        outcome.record = authorize_owned(record, owner, who)
    except DomainError as error:
        outcome.error = error


@when(parsers.parse('"{email}" opens an absent record'))
def opens_absent(world: FakeWorld, outcome: Outcome, email: str) -> None:
    open_record(outcome, None, None, identity_of(world, email))


@when(parsers.parse('"{email}" opens a record owned by "{owner}"'))
def opens_owned(world: FakeWorld, outcome: Outcome, email: str, owner: str) -> None:
    open_record(outcome, "the record", user_of(world, owner).id, identity_of(world, email))


@when(parsers.parse('a POST to "{path}" arrives from origin "{origin}"'))
def cross_origin_post(fake_container: Container, outcome: Outcome, path: str, origin: str) -> None:
    response = Client().post(path, {"email": "admin@example.org"}, headers={"Origin": origin})
    outcome.status = response.status_code
    outcome.body = response.json() if path.startswith("/api/") else {"code": "forbidden"}


@given(parsers.parse('a passwordless {role} "{email}" with an open session'))
def passwordless_with_session(world: FakeWorld, web: Client, role: str, email: str) -> None:
    user = add_user(world, email, role, None)
    token = "patient-session-token"
    world.sessions.add(
        Session.after_password(
            token=token, user_id=user.id, role=user.role, user_agent="test", at=world.clock.now()
        )
    )
    web.cookies[settings.SESSION_COOKIE_NAME] = token


@when(parsers.parse('"{email}" signs in on the sign-in page with "{password}"'))
def signs_in_on_page(web: Client, outcome: Outcome, email: str, password: str) -> None:
    outcome.password = password
    response = web.post("/sign-in", {"email": email, "password": password})
    outcome.status = response.status_code
    outcome.body = {"location": response.get("Location", "")}


@when(parsers.parse('they choose the new password "{new}" on the password page'))
def chooses_password(web: Client, outcome: Outcome, new: str) -> None:
    response = web.post(
        "/account/password", {"current_password": outcome.password, "new_password": new}
    )
    assert response.status_code == 302


@when(parsers.parse('"{email}" signs in through the API with "{password}"'))
def signs_in_api(web: Client, outcome: Outcome, email: str, password: str) -> None:
    response = web.post(
        "/api/v1/auth/login",
        {"email": email, "password": password},
        content_type="application/json",
    )
    outcome.status = response.status_code
    outcome.body = response.json()


@when("they sign out through the API")
def signs_out_api(web: Client, outcome: Outcome) -> None:
    outcome.status = web.post("/api/v1/auth/logout").status_code


@then(parsers.parse('they land on "{home}"'))
def lands_on(outcome: Outcome, home: str) -> None:
    assert outcome.status == 302
    assert outcome.body["location"] == home


@then(parsers.parse('the page "{page}" opens'))
def page_opens(web: Client, page: str) -> None:
    assert web.get(page).status_code == 200


@then(parsers.parse('the page "{page}" sends them to "{target}"'))
def page_redirects(web: Client, page: str, target: str) -> None:
    response = web.get(page)
    assert response.status_code == 302
    assert response["Location"] == target


@then(parsers.parse('the page "{page}" is forbidden'))
def page_forbidden(web: Client, page: str) -> None:
    response = web.get(page)
    assert response.status_code == 403
    assert "Accès refusé" in response.content.decode()


@then(parsers.parse('the page "{page}" shows no link to "{link}"'))
def page_without_link(web: Client, page: str, link: str) -> None:
    response = web.get(page)
    assert response.status_code == 200
    assert f'href="{link}"' not in response.content.decode()


@then(parsers.parse('the API answers 200 with role "{role}" and home "{home}"'))
def api_login_ok(outcome: Outcome, role: str, home: str) -> None:
    assert outcome.status == 200
    assert outcome.body == {"role": role, "home": home}


@then("the API answers 204")
def api_no_content(outcome: Outcome) -> None:
    assert outcome.status == 204


@then(parsers.parse("a {role} session lasting {hours:d} hours is opened"))
def session_opened(world: FakeWorld, outcome: Outcome, role: str, hours: int) -> None:
    assert outcome.error is None
    assert outcome.signed_in is not None
    assert outcome.signed_in.role is Role(role)
    assert outcome.signed_in.expires_at == world.clock.now() + timedelta(hours=hours)
    [session] = [
        s for s in world.sessions.rows.values() if s.expires_at == outcome.signed_in.expires_at
    ]
    assert session.token_hash != outcome.signed_in.token


@then(parsers.parse('the audit holds "{action}" with email domain "{domain}"'))
def audited_with_domain(world: FakeWorld, action: str, domain: str) -> None:
    [entry] = [e for e in world.audit.entries if e.action == action]
    assert dict(entry.metadata) == {"email_domain": domain}


@then(parsers.parse('the audit holds "{action}"'))
def audited(world: FakeWorld, action: str) -> None:
    assert action in world.audit.actions()


@then(parsers.parse('the audit holds "{action}" without metadata'))
def audited_bare(world: FakeWorld, action: str) -> None:
    [entry] = [e for e in world.audit.entries if e.action == action]
    assert entry.metadata == ()


@then(parsers.parse('the last login time of "{email}" is now'))
def last_login(world: FakeWorld, email: str) -> None:
    assert user_of(world, email).last_login_at == world.clock.now()


@then(parsers.parse('sign-in is refused with "{message}"'))
def refused_with(outcome: Outcome, message: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == "unauthenticated"
    assert outcome.error.message == message


@then(parsers.parse("exactly {count:d} password check ran"))
def checks_ran(world: FakeWorld, count: int) -> None:
    assert world.hasher.verifications == count


@then("no session is opened")
def no_session(world: FakeWorld) -> None:
    assert world.sessions.rows == {}


@then(parsers.parse("the session expires {days:d} days from now"))
def expires_in(world: FakeWorld, outcome: Outcome, days: int) -> None:
    assert outcome.identity is not None
    assert outcome.identity.session_expires_at == world.clock.now() + timedelta(days=days)
    [session] = world.sessions.rows.values()
    assert session.expires_at == outcome.identity.session_expires_at


@then("the session was renewed")
def renewed(outcome: Outcome) -> None:
    assert outcome.identity is not None
    assert outcome.identity.session_renewed is True


@then("nobody is identified")
def nobody(outcome: Outcome) -> None:
    assert outcome.identity is None


@then(parsers.parse('"{email}" no longer has to change password'))
def no_forced_change(world: FakeWorld, email: str) -> None:
    assert user_of(world, email).must_change_password is False


@then(parsers.parse('"{email}" still has to change password'))
def forced_change(world: FakeWorld, email: str) -> None:
    assert user_of(world, email).must_change_password is True


@then(parsers.parse('"{email}" can sign in with "{password}"'))
def can_sign_in(world: FakeWorld, email: str, password: str) -> None:
    assert world.app.sign_in.execute(email=email, password=password, user_agent="pytest")


@then(parsers.parse('the change is refused as invalid on "{field}"'))
def invalid_on(outcome: Outcome, field: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == "invalid_input"
    assert [f["field"] for f in outcome.error.details["fields"]] == [field]


@then(parsers.parse('the change is refused as "{code}"'))
@then(parsers.parse('access is refused as "{code}"'))
def refused_as(outcome: Outcome, code: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code.value == code


@then("the record is returned")
def record_returned(outcome: Outcome) -> None:
    assert outcome.error is None
    assert outcome.record == "the record"


@then(parsers.parse('the response is {status:d} "{code}"'))
def response_is(outcome: Outcome, status: int, code: str) -> None:
    assert outcome.status == status
    assert outcome.body["code"] == code


@then("nothing is audited")
def nothing_audited(world: FakeWorld) -> None:
    assert world.audit.entries == []
