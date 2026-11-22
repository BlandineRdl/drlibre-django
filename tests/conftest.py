import uuid
from collections.abc import Iterator
from typing import Any

import pytest
import redis
from django.conf import settings
from django.db import connection
from django.test import Client

from config.settings import env, smtp_mailers
from drlibre.bootstrap.container import Container, use_container
from drlibre.identity.domain.user import Role
from tests.builders import stored_session, stored_user
from tests.fakes.database_probe import InMemoryDatabaseProbe
from tests.fakes.world import FakeWorld

# Booking's steps, one module per area; pytest only reads plugins from the top conftest.
pytest_plugins = [
    "tests.fhir.directory_steps",
    "tests.fhir.slot_steps",
    "tests.fhir.patient_steps",
    "tests.use_cases.booking.steps_scene",
    "tests.use_cases.booking.steps_holds",
    "tests.use_cases.booking.steps_changes",
    "tests.use_cases.booking.steps_reminders",
    "tests.use_cases.booking.steps_pages",
    "tests.use_cases.booking.steps_clinician",
    "tests.use_cases.booking.steps_clinician_reads",
    "tests.use_cases.booking.steps_waitlist",
    "tests.use_cases.booking.steps_waitlist_offers",
    "tests.use_cases.booking.steps_admin",
    "tests.use_cases.booking.steps_admin_reads",
]


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup: None, django_db_blocker: Any) -> None:
    """Transactional tests flush with TRUNCATE: only the test database lets it empty the audit."""
    with django_db_blocker.unblock(), connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE audit_auditentryrecord DISABLE TRIGGER audit_entries_never_truncated"
        )


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


@pytest.fixture(autouse=True)
def rate_limit_prefix(settings: Any) -> Iterator[None]:
    """Each test counts rate limits under its own Redis prefix and flushes it afterwards."""
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    settings.RATE_LIMIT_PREFIX = prefix
    use_container(None)
    yield
    use_container(None)
    try:
        client = redis.Redis.from_url(settings.REDIS_URL)
        for key in client.scan_iter(f"{prefix}:*"):
            client.delete(key)
    except redis.RedisError:
        pass  # No Redis, no keys: tests without the compose services.
