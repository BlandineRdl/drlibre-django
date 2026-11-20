from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from config.settings import env
from drlibre.bootstrap.container import Container, use_container
from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from tests.fakes.clock import FixedClock
from tests.fakes.database_probe import InMemoryDatabaseProbe
from tests.fakes.in_memory_mailer import InMemoryMailer


@pytest.fixture
def fake_probe() -> InMemoryDatabaseProbe:
    return InMemoryDatabaseProbe()


@pytest.fixture
def fake_container(fake_probe: InMemoryDatabaseProbe) -> Iterator[Container]:
    clock = FixedClock(datetime(2026, 11, 20, 10, tzinfo=UTC))
    wired = Container(
        check_health=CheckHealthUseCase(clock=clock, database=fake_probe),
        mailer=InMemoryMailer(),
    )
    use_container(wired)
    yield wired
    use_container(None)


@pytest.fixture
def mailpit_smtp(settings: Any) -> str:
    """Route the default mailer to Mailpit, undoing the test locmem swap; returns its API URL."""
    settings.MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {"host": env.email_host, "port": env.email_port, "timeout": 10},
        }
    }
    return f"http://{env.email_host}:8025/api/v1"
