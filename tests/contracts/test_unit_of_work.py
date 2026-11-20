from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from tests.fakes.audit_log import InMemoryAuditLog
from tests.fakes.unit_of_work import InMemoryUnitOfWork

REAL = [pytest.mark.integration, pytest.mark.django_db]

type Stored = Callable[[Id], int]


class WriteFailedError(RuntimeError):
    pass


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def unit(request: pytest.FixtureRequest) -> tuple[UnitOfWork, AuditLog, Stored]:
    if request.param == "fake":
        log = InMemoryAuditLog()
        return InMemoryUnitOfWork(log), log, lambda e: sum(x.entity_id == e for x in log.entries)
    return (
        DjangoUnitOfWork(),
        DjangoAuditLog(),
        lambda e: AuditEntryRecord.objects.filter(entity_id=e.value).count(),
    )


def entry(entity: Id) -> AuditEntry:
    return AuditEntry.from_event(
        actor=None,
        action="test.written",
        entity_type="test",
        entity_id=entity,
        at=datetime(2026, 11, 20, 10, tzinfo=UTC),
    )


def test_a_clean_unit_keeps_its_writes(unit: tuple[UnitOfWork, AuditLog, Stored]) -> None:
    """Spec §4: one transaction per logical change, its audit entry included."""
    uow, log, stored = unit
    entity = Id()

    with uow:
        log.record(entry(entity))

    assert stored(entity) == 1


def test_a_failing_unit_writes_nothing(unit: tuple[UnitOfWork, AuditLog, Stored]) -> None:
    """Spec §4: if part of the change fails, nothing of it is written."""
    uow, log, stored = unit
    entity = Id()

    def change_then_fail() -> None:
        with uow:
            log.record(entry(entity))
            raise WriteFailedError

    with pytest.raises(WriteFailedError):
        change_then_fail()

    assert stored(entity) == 0


def test_a_nested_unit_joins_the_outer_one(unit: tuple[UnitOfWork, AuditLog, Stored]) -> None:
    uow, log, stored = unit
    entity = Id()

    def nested_then_fail() -> None:
        with uow:
            with uow:
                log.record(entry(entity))
            raise WriteFailedError

    with pytest.raises(WriteFailedError):
        nested_then_fail()

    assert stored(entity) == 0
