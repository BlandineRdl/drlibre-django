import dataclasses
from collections.abc import Iterator
from datetime import timedelta
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import container, use_container
from drlibre.identity.domain.session import hash_token
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.django.models import ApiTokenRecord
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import patient_user
from tests.fakes.world import FakeWorld

scenarios(
    "../../features/identity/un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.feature"
)


@dataclasses.dataclass
class Scene:
    token: str = ""
    printed: str = ""
    response: Any = None


@pytest.fixture
def scene(world: FakeWorld) -> Iterator[Scene]:
    use_container(world.app)
    yield Scene()
    use_container(None)


def issue(email: str) -> str:
    out = StringIO()
    call_command("api_token", email, stdout=out)
    return out.getvalue().strip()


def user_of(world: FakeWorld, email: str) -> Any:
    return next(u for u in world.users.rows.values() if u.email.value == email)


@given(parsers.parse('an active "{role}" "{email}"'))
def active_user(world: FakeWorld, scene: Scene, role: str, email: str) -> None:
    world.users.save(patient_user(Id(), email=email, role=Role(role)))


@given(parsers.parse('an active "{role}" "{email}" holding a token'))
def user_with_token(world: FakeWorld, scene: Scene, role: str, email: str) -> None:
    active_user(world, scene, role, email)
    scene.token = issue(email)


@given("the client sends another token instead")
def another_token(scene: Scene) -> None:
    scene.token = "not-a-token"


@given("the token has expired")
def expired(world: FakeWorld) -> None:
    world.clock.at += timedelta(days=90)


@given(parsers.parse('the command revokes the tokens of "{email}"'))
def revoked(email: str) -> None:
    call_command("api_token", email, "--revoke", stdout=StringIO())


@given(parsers.parse('"{email}" is deactivated'))
def deactivated(world: FakeWorld, email: str) -> None:
    world.users.save(dataclasses.replace(user_of(world, email), active=False))


@given(parsers.parse('"{email}" must change their password'))
def must_change(world: FakeWorld, email: str) -> None:
    world.users.save(dataclasses.replace(user_of(world, email), must_change_password=True))


@when(parsers.parse('the administration command issues a token for "{email}"'))
def command_issues(scene: Scene, email: str) -> None:
    scene.printed = issue(email)


@when(parsers.parse('the client calls "{method}" "{path}" with that token'))
def client_calls(scene: Scene, method: str, path: str) -> None:
    headers = {"Authorization": f"Bearer {scene.token}"}
    scene.response = Client().generic(method, path, headers=headers)


@then("the command prints the token once")
def printed_once(world: FakeWorld, scene: Scene) -> None:
    assert world.tokens.issued == 1
    assert scene.printed == "token-1"


@then(parsers.parse('only the hash of the token is stored for "{email}"'))
def only_hash(world: FakeWorld, scene: Scene, email: str) -> None:
    (stored,) = world.api_tokens.rows.values()
    assert stored.user_id == user_of(world, email).id
    assert stored.token_hash == hash_token(scene.printed)
    assert scene.printed not in repr(stored)


@then(parsers.parse('the audit log holds "{action}" without personal data'))
def audited(world: FakeWorld, action: str) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert "example.org" not in repr(entry)


@then(parsers.parse("the answer is {status:d}"))
def answer_is(scene: Scene, status: int) -> None:
    assert scene.response.status_code == status, scene.response.content


@then(
    parsers.parse(
        'the answer is {status:d} with an OperationOutcome "{issue}" and the code "{code}"'
    )
)
def outcome_is(scene: Scene, status: int, issue: str, code: str) -> None:
    body = scene.response.json()
    assert scene.response.status_code == status
    assert scene.response["Content-Type"].startswith("application/fhir+json")
    assert body["resourceType"] == "OperationOutcome"
    (found,) = body["issue"]
    assert found["code"] == issue
    assert found["details"]["coding"][0]["code"] == code


@when("the demo seed runs twice")
def seed_twice() -> None:
    from scripts import seed

    use_container(None)
    seed.main()
    seed.main()


@then(
    parsers.parse('the demo tokens "{admin}", "{clinician}" and "{patient}" are stored once each')
)
def demo_tokens_stored(admin: str, clinician: str, patient: str) -> None:
    hashes = [hash_token(t) for t in (admin, clinician, patient)]
    assert ApiTokenRecord.objects.filter(token_hash__in=hashes).count() == 3


@then("each demo token authenticates a user of its role")
def demo_tokens_authenticate() -> None:
    roles = {
        "demo-admin-token": Role.ADMIN,
        "demo-clinician-token": Role.CLINICIAN,
        "demo-patient-token": Role.PATIENT,
    }
    for token, role in roles.items():
        identity = container().authenticate_token.execute(token=token)
        assert identity is not None, token
        assert identity.role is role
