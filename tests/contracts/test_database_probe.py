import pytest

from drlibre.health.application.ports.outbound import DatabaseProbe
from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe
from tests.fakes.database_probe import InMemoryDatabaseProbe


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="django", marks=[pytest.mark.integration, pytest.mark.django_db]),
    ]
)
def probe(request: pytest.FixtureRequest) -> DatabaseProbe:
    return InMemoryDatabaseProbe() if request.param == "fake" else DjangoDatabaseProbe()


def test_reachable_database_is_reported_up(probe: DatabaseProbe) -> None:
    assert probe.is_up() is True
