import uuid
from datetime import UTC, datetime

import pytest

from drlibre.identity.application.ports.outbound import ApiTokens, Users
from drlibre.identity.domain.api_token import ApiToken
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.repositories import DjangoApiTokens, DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.fakes.api_tokens import InMemoryApiTokens
from tests.fakes.users import InMemoryUsers

AT = datetime(2026, 11, 22, 10, tzinfo=UTC)
REAL = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def stores(request: pytest.FixtureRequest) -> tuple[Users, ApiTokens]:
    if request.param == "fake":
        return InMemoryUsers(), InMemoryApiTokens()
    return DjangoUsers(), DjangoApiTokens()


def a_user(users: Users) -> Id:
    user = User(
        id=Id(),
        email=Email(f"user-{uuid.uuid4().hex[:8]}@example.org"),
        full_name="Léa Martin",
        role=Role.PATIENT,
        active=True,
        password_hash=None,
        must_change_password=False,
        last_login_at=None,
        created_at=AT,
        updated_at=AT,
    )
    users.save(user)
    return user.id


def a_token(user_id: Id) -> ApiToken:
    return ApiToken.issue(token=uuid.uuid4().hex, user_id=user_id, label="cli", days=90, at=AT)


def test_a_token_is_found_by_its_hash_only(stores: tuple[Users, ApiTokens]) -> None:
    users, tokens = stores
    token = a_token(a_user(users))

    tokens.add(token)

    assert tokens.by_token_hash(token.token_hash) == token
    assert tokens.by_token_hash("0" * 64) is None


def test_revoking_removes_every_token_of_the_user_and_spares_others(
    stores: tuple[Users, ApiTokens],
) -> None:
    users, tokens = stores
    user, other = a_user(users), a_user(users)
    mine, also_mine, theirs = a_token(user), a_token(user), a_token(other)
    for token in (mine, also_mine, theirs):
        tokens.add(token)

    assert tokens.delete_for_user(user) == 2

    assert tokens.by_token_hash(mine.token_hash) is None
    assert tokens.by_token_hash(also_mine.token_hash) is None
    assert tokens.by_token_hash(theirs.token_hash) == theirs
