from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from drlibre.bootstrap.container import Container, use_container
from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from tests.fakes.clock import FixedClock
from tests.fakes.database_probe import InMemoryDatabaseProbe


@pytest.fixture
def fake_probe() -> InMemoryDatabaseProbe:
    return InMemoryDatabaseProbe()


@pytest.fixture
def fake_container(fake_probe: InMemoryDatabaseProbe) -> Iterator[Container]:
    clock = FixedClock(datetime(2026, 11, 20, 10, tzinfo=UTC))
    wired = Container(check_health=CheckHealthUseCase(clock=clock, database=fake_probe))
    use_container(wired)
    yield wired
    use_container(None)
