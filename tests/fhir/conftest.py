from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from drlibre.bootstrap.container import container
from drlibre.identity.domain.user import Role, User
from tests.builders import stored_user

type Call = Callable[..., Any]


@pytest.fixture
def fhir_client() -> Client:
    return Client()


def token_for(user: User) -> str:
    """A bearer token issued through the real use case, as the administration command does."""
    return container().issue_api_token.execute(user_email=user.email.value, label="test")


@pytest.fixture
def role_token(db: None) -> Callable[..., str]:
    """A token of a new stored user of the role, e.g. `role_token(Role.ADMIN)`."""

    def issue(role: Role, **user: Any) -> str:
        return token_for(stored_user(role, **user))

    return issue


@pytest.fixture
def call(fhir_client: Client) -> Call:
    """One FHIR request, with the token as a bearer when one is given."""

    def send(method: str, path: str, *, token: str | None = None, **extra: Any) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return fhir_client.generic(method, path, headers=headers, **extra)

    return send
