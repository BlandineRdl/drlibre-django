import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import unquote

import pytest
from django.conf import settings
from django.test import Client
from django.utils.html import escape
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.session import hash_token
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import patient_user
from tests.fakes.world import FakeWorld

scenarios("../../features/identity/le_patient_se_connecte_par_un_lien_recu_par_email.feature")

LINK_SUBJECT = "Votre lien de connexion"
SENT_MESSAGE = "Si cette adresse est celle d'un compte patient"
NETWORK = "10.0.0.1"


@dataclass
class Scene:
    responses: list[Any] = field(default_factory=list)
    last: Any = None
    users_before: int = 0
    signed_at: Any = None
    log_messages: list[str] = field(default_factory=list)


@pytest.fixture
def scene(world: FakeWorld) -> Iterator[Scene]:
    use_container(world.app)
    yield Scene()
    use_container(None)


def tokens(world: FakeWorld) -> list[str]:
    found = (re.search(r"token=([^\s&]+)", m.body) for m in world.outbox.queued)
    return [unquote(hit.group(1)) for hit in found if hit]


def link_emails(world: FakeWorld) -> list[Any]:
    return [m for m in world.outbox.queued if m.subject == LINK_SUBJECT]


def add_user(
    world: FakeWorld,
    email: str,
    *,
    role: Role = Role.PATIENT,
    active: bool = True,
    password: str | None = None,
) -> None:
    hashed = world.hasher.hash(password) if password else None
    world.users.save(
        patient_user(Id(), email=email, role=role, active=active, password_hash=hashed)
    )


def ask(client: Client, scene: Scene, email: str, network: str = NETWORK) -> Any:
    scene.last = client.post("/sign-in/link/request", {"link_email": email}, REMOTE_ADDR=network)
    scene.responses.append(scene.last)
    return scene.last


def press_continue(client: Client, world: FakeWorld, scene: Scene, token: str) -> None:
    client.get("/sign-in/link", {"token": token})
    scene.signed_at = world.clock.now()
    scene.last = client.post("/sign-in/link", {"token": token})


@given('an active passwordless patient "lea@example.org"')
def background_patient(world: FakeWorld) -> None:
    add_user(world, "lea@example.org")


@given(parsers.parse('an active {role} account "{email}"'))
def role_account(world: FakeWorld, role: str, email: str) -> None:
    add_user(world, email, role=Role(role))


@given(parsers.parse('an inactive {role} account "{email}"'))
def inactive_account(world: FakeWorld, role: str, email: str) -> None:
    add_user(world, email, role=Role(role), active=False)


@given("no other account")
def no_other_account() -> None:
    return None


@given(parsers.parse('a patient "{email}" with a password'))
def patient_with_password(world: FakeWorld, email: str) -> None:
    add_user(world, email, password="correct-horse-1")


@given(parsers.parse('a patient "{email}" without a password'))
def patient_without_password(world: FakeWorld, email: str) -> None:
    add_user(world, email)


@given(parsers.parse('"{email}" asked for a link'))
def asked(client: Client, scene: Scene, email: str) -> None:
    ask(client, scene, email)


@given(parsers.parse('"{email}" asked for a link {times:d} times'))
def asked_times(client: Client, scene: Scene, email: str, times: int) -> None:
    for _ in range(times):
        ask(client, scene, email)


@given(parsers.parse('{count:d} requests for distinct patients from the network "{network}"'))
def many_requests(world: FakeWorld, client: Client, scene: Scene, count: int, network: str) -> None:
    for number in range(count):
        email = f"patient{number}@example.org"
        add_user(world, email)
        ask(client, scene, email, network)


@given(parsers.parse("{minutes:d} minutes pass"))
@when(parsers.parse("{minutes:d} minutes pass"))
def minutes_pass(world: FakeWorld, minutes: int) -> None:
    world.clock.at += timedelta(minutes=minutes)


@given(parsers.parse("the link is {state}"))
def link_state(world: FakeWorld, state: str) -> None:
    (link,) = world.links.rows.values()
    now = world.clock.now()
    if state == "expired":
        world.clock.at += timedelta(minutes=16)
    elif state == "used":
        world.links.save(link.used(now))
    else:
        world.links.save(link.cancelled(now))


@when(parsers.parse('"{email}" asks for a link on the sign-in page'))
def ask_on_page(world: FakeWorld, client: Client, scene: Scene, email: str) -> None:
    scene.users_before = len(world.users.rows)
    ask(client, scene, email)


@when(parsers.parse('"{email}" asks for a link from the network "{network}"'))
def ask_from_network(client: Client, scene: Scene, email: str, network: str) -> None:
    ask(client, scene, email, network)


@when("the patient opens the link")
def open_link(world: FakeWorld, client: Client, scene: Scene) -> None:
    scene.last = client.get("/sign-in/link", {"token": tokens(world)[-1]})


@given('the patient opens the link and presses "Continuer"')
@when('the patient opens the link and presses "Continuer"')
def open_and_continue(world: FakeWorld, client: Client, scene: Scene) -> None:
    press_continue(client, world, scene, tokens(world)[-1])


@when('the patient opens the first link and presses "Continuer"')
def open_first_and_continue(world: FakeWorld, client: Client, scene: Scene) -> None:
    press_continue(client, world, scene, tokens(world)[0])


@when("13 hours pass and the patient visits their session")
def visit_later(world: FakeWorld, client: Client) -> None:
    world.clock.at += timedelta(hours=13)
    assert client.get("/portal/").status_code == 200


@when(parsers.parse('the API is asked for a link for "{first}" and for "{second}"'))
def api_asks(client: Client, scene: Scene, first: str, second: str) -> None:
    scene.responses = [
        client.post(
            "/api/v1/auth/link",
            json.dumps({"email": email}),
            content_type="application/json",
            REMOTE_ADDR=NETWORK,
        )
        for email in (first, second)
    ]


@when("the API verifies the link token")
def api_verifies(world: FakeWorld, client: Client, scene: Scene) -> None:
    scene.signed_at = world.clock.now()
    scene.last = client.post(
        "/api/v1/auth/link/verify",
        json.dumps({"token": tokens(world)[-1]}),
        content_type="application/json",
    )


@then("the page says a link was sent if the address has a patient account")
def page_says_sent(scene: Scene) -> None:
    assert scene.last is not None
    assert scene.last.status_code == 200
    assert escape(SENT_MESSAGE) in scene.last.content.decode()


@then("both answers are the same page")
def same_page(scene: Scene) -> None:
    first, second = scene.responses
    assert first.status_code == second.status_code == 200
    assert first.content == second.content


@then("no email was sent")
def nothing_sent(world: FakeWorld) -> None:
    assert world.outbox.queued == []


@then("no link and no account were created")
def nothing_created(world: FakeWorld, scene: Scene) -> None:
    assert world.links.rows == {}
    assert len(world.users.rows) == scene.users_before


@then(parsers.parse('the patient lands on "{path}"'))
def lands(client: Client, scene: Scene, path: str) -> None:
    assert scene.last is not None
    assert scene.last.status_code == 302
    assert scene.last["Location"] == path
    assert settings.SESSION_COOKIE_NAME in scene.last.cookies
    assert client.get(path).status_code == 200


@then("the address holds no token")
def address_without_token(scene: Scene, world: FakeWorld) -> None:
    assert scene.last is not None
    assert not any(token in scene.last["Location"] for token in tokens(world))


@then("no session was opened")
def no_session(world: FakeWorld, scene: Scene) -> None:
    assert world.sessions.rows == {}
    assert scene.last is not None
    assert settings.SESSION_COOKIE_NAME not in scene.last.cookies


@then("only one session exists")
def one_session(world: FakeWorld) -> None:
    assert len(world.sessions.rows) == 1


@then(parsers.parse("{count:d} link emails were sent in all"))
def link_email_count(world: FakeWorld, count: int) -> None:
    assert len(link_emails(world)) == count


@then('the page offers a "Continuer" button')
def offers_continue(scene: Scene) -> None:
    assert scene.last is not None
    body = scene.last.content.decode()
    assert scene.last.status_code == 200
    assert ">Continuer</button>" in body


@then("the link is still usable")
def still_usable(world: FakeWorld) -> None:
    link = world.links.by_token_hash(hash_token(tokens(world)[-1]))
    assert link is not None
    assert link.usable(world.clock.now())


@then("the session still ends 24 hours after the sign-in")
def session_never_extended(world: FakeWorld, scene: Scene) -> None:
    (session,) = world.sessions.rows.values()
    assert session.expires_at == scene.signed_at + timedelta(hours=24)
    assert not session.extendable


@then("the page offers to request a new link")
def offers_new_link(scene: Scene) -> None:
    assert scene.last is not None
    body = scene.last.content.decode()
    assert scene.last.status_code == 401
    assert escape("Ce lien n'est plus valable") in body
    assert "Recevoir un lien" in body


@then("only the link email holds a link that signs in")
def only_link_email(world: FakeWorld) -> None:
    with_token = [m for m in world.outbox.queued if "token=" in m.body]
    assert len(with_token) == 1
    assert with_token[0].subject == LINK_SUBJECT


@then("the logs hold no token")
def logs_without_token(world: FakeWorld, caplog: pytest.LogCaptureFixture) -> None:
    assert tokens(world)
    text = " ".join(f"{r.msg} {r.getMessage()}" for r in caplog.records)
    assert "/sign-in/link" in text
    assert not any(token in text for token in tokens(world))


@then(parsers.parse('the audit holds one "{action}" entry with only the email domain'))
def audit_domain_only(world: FakeWorld, action: str) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert len(entries) == 1
    assert dict(entries[0].metadata) == {"email_domain": "example.org"}


@then("both API answers are identical with status 202")
def api_identical(scene: Scene) -> None:
    first, second = scene.responses
    assert first.status_code == second.status_code == 202
    assert first.content == second.content


@then("the API answer is 200 with a 24 hour session cookie")
def api_session(world: FakeWorld, scene: Scene) -> None:
    assert scene.last is not None
    assert scene.last.status_code == 200
    assert settings.SESSION_COOKIE_NAME in scene.last.cookies
    (session,) = world.sessions.rows.values()
    assert session.expires_at == scene.signed_at + timedelta(hours=24)
    assert not session.extendable


@pytest.fixture(autouse=True)
def capture_info(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
