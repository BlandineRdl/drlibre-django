import pytest
from django.test import Client

from drlibre.bootstrap.container import Container
from tests.fakes.database_probe import InMemoryDatabaseProbe


@pytest.mark.usefixtures("fake_container")
def test_healthy_service_answers_200(client: Client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "up",
        "checked_at": "2026-11-20T10:00:00Z",
    }


def test_unreachable_database_answers_503_degraded(
    client: Client, fake_container: Container, fake_probe: InMemoryDatabaseProbe
) -> None:
    fake_probe.up = False

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
