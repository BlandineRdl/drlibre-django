from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from config.settings import env, smtp_mailers
from drlibre.bootstrap.container import Container, use_container
from drlibre.identity.domain.user import Role
from tests.builders import stored_session, stored_user
from tests.fakes.database_probe import InMemoryDatabaseProbe
from tests.fakes.world import FakeWorld


@pytest.fixture
def world() -> FakeWorld:
    return FakeWorld()


@pytest.fixture
def fake_probe(world: FakeWorld) -> InMemoryDatabaseProbe:
    return world.database


@pytest.fixture
def fake_container(world: FakeWorld) -> Iterator[Container]:
    use_container(world.app)
    yield world.app
    use_container(None)


@pytest.fixture
def mailpit_smtp(settings: Any) -> str:
    """Route the default mailer to Mailpit, undoing the test locmem swap; returns its API URL."""
    settings.MAILERS = smtp_mailers()
    return f"http://{env.email_host}:8025/api/v1"


@pytest.fixture
def admin_client(client: Client, db: None) -> Client:
    """A Django client signed in as a fresh admin, through a real stored session."""
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(stored_user(Role.ADMIN))
    return client
