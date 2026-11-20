from collections.abc import Iterator

import pytest
from django.db import connections

from drlibre.health.application.ports.outbound import DatabaseProbe
from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe
from tests.fakes.database_probe import InMemoryDatabaseProbe

ADAPTERS = [
    pytest.param("fake", id="in-memory"),
    pytest.param("real", id="django", marks=[pytest.mark.integration, pytest.mark.django_db]),
]


@pytest.fixture(params=ADAPTERS)
def probe(request: pytest.FixtureRequest) -> DatabaseProbe:
    return InMemoryDatabaseProbe() if request.param == "fake" else DjangoDatabaseProbe()


@pytest.fixture(params=ADAPTERS)
def down_probe(request: pytest.FixtureRequest) -> Iterator[DatabaseProbe]:
    if request.param == "fake":
        yield InMemoryDatabaseProbe(up=False)
        return
    # Separate connection to a closed port, so the shared one stays healthy.
    default = connections["default"]
    unreachable = type(default)({**default.settings_dict, "PORT": 1}, alias="unreachable")
    yield DjangoDatabaseProbe(unreachable)
    unreachable.close()


def test_reachable_database_is_reported_up(probe: DatabaseProbe) -> None:
    assert probe.is_up() is True


def test_unreachable_database_is_reported_down(down_probe: DatabaseProbe) -> None:
    assert down_probe.is_up() is False
