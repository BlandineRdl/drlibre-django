import dataclasses
from collections.abc import Iterator

import pytest
from django.test import Client

from drlibre.bootstrap.container import use_container
from drlibre.health.application.ports.inbound import CheckHealth
from drlibre.health.domain.health_report import HealthReport
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from tests.fakes.world import FakeWorld


class RejectingCheckHealth(CheckHealth):
    def execute(self) -> HealthReport:
        raise DomainError(ErrorCode.CONFLICT, "Slot taken", {"slot": "10:00"})


@pytest.fixture
def rejecting_container(world: FakeWorld) -> Iterator[None]:
    use_container(dataclasses.replace(world.app, check_health=RejectingCheckHealth()))
    yield
    use_container(None)


@pytest.mark.usefixtures("rejecting_container")
def test_domain_error_answers_its_status_with_code_message_details(client: Client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 409
    assert response.json() == {
        "code": "conflict",
        "message": "Slot taken",
        "details": {"slot": "10:00"},
    }
