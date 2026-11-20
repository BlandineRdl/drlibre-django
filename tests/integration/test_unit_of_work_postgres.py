from datetime import UTC, datetime

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_log import AuditLogUnavailableError, InMemoryAuditLog

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def entry(entity: Id) -> AuditEntry:
    return AuditEntry.from_event(
        actor=None,
        action="test.written",
        entity_type="test",
        entity_id=entity,
        at=datetime(2026, 11, 20, 10, tzinfo=UTC),
    )


def test_a_failing_audit_rolls_back_the_write_of_the_same_unit() -> None:
    entity = Id()

    def write_then_fail_to_audit() -> None:
        with DjangoUnitOfWork():
            DjangoAuditLog().record(entry(entity))
            InMemoryAuditLog(failing=True).record(entry(entity))

    with pytest.raises(AuditLogUnavailableError):
        write_then_fail_to_audit()

    assert not AuditEntryRecord.objects.filter(entity_id=entity.value).exists()


def test_a_clean_unit_commits_its_writes() -> None:
    entity = Id()

    with DjangoUnitOfWork():
        DjangoAuditLog().record(entry(entity))

    assert AuditEntryRecord.objects.filter(entity_id=entity.value).count() == 1
