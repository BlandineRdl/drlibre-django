from datetime import datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from drlibre.health.domain.health_report import HealthReport
from tests.fakes.clock import FixedClock
from tests.fakes.database_probe import InMemoryDatabaseProbe

scenarios("../features/health.feature")


@pytest.fixture
def probe() -> InMemoryDatabaseProbe:
    return InMemoryDatabaseProbe()


@given(parsers.parse('the clock reads "{at}"'), target_fixture="clock")
def clock(at: str) -> FixedClock:
    return FixedClock(datetime.fromisoformat(at))


@given("the database is up")
def database_up(probe: InMemoryDatabaseProbe) -> None:
    probe.up = True


@given("the database is down")
def database_down(probe: InMemoryDatabaseProbe) -> None:
    probe.up = False


@when("the health is checked", target_fixture="report")
def check(clock: FixedClock, probe: InMemoryDatabaseProbe) -> HealthReport:
    return CheckHealthUseCase(clock=clock, database=probe).execute()


@then(parsers.parse('the status is "{status}"'))
def status_is(report: HealthReport, status: str) -> None:
    assert report.status.value == status


@then(parsers.parse('the database is reported "{state}"'))
def database_is(report: HealthReport, state: str) -> None:
    assert report.database.value == state


@then(parsers.parse('the report is dated "{at}"'))
def dated(report: HealthReport, at: str) -> None:
    assert report.checked_at == datetime.fromisoformat(at)
