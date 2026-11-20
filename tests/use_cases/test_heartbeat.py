from typing import cast

import pytest
import structlog
from celery import Task

from drlibre.interfaces.jobs.tasks import heartbeat
from tests.fakes.database_probe import InMemoryDatabaseProbe

task = cast(Task, heartbeat)


@pytest.mark.usefixtures("fake_container")
def test_heartbeat_reports_health_through_the_use_case() -> None:
    with structlog.testing.capture_logs(
        processors=[structlog.contextvars.merge_contextvars]
    ) as logs:
        result = task.apply().get()

    assert result == {"status": "ok", "database": "up"}
    assert logs[-1]["event"] == "heartbeat"
    assert "correlation_id" in logs[-1]


@pytest.mark.usefixtures("fake_container")
def test_heartbeat_reports_a_down_database(fake_probe: InMemoryDatabaseProbe) -> None:
    fake_probe.up = False

    assert task.apply().get() == {"status": "degraded", "database": "down"}
