from collections.abc import Callable
from datetime import UTC, datetime

import pytest
import structlog

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_log import InMemoryAuditLog

type Stored = Callable[[Id], list[tuple[str, str, dict[str, object]]]]


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="django", marks=[pytest.mark.integration, pytest.mark.django_db]),
    ]
)
def log_and_store(request: pytest.FixtureRequest) -> tuple[AuditLog, Stored]:
    if request.param == "fake":
        fake = InMemoryAuditLog()
        return fake, lambda entity: [
            (
                e.action,
                e.entity_type,
                {k: list(v) if isinstance(v, tuple) else v for k, v in e.metadata},
            )
            for e in fake.entries
            if e.entity_id == entity
        ]

    def stored(entity: Id) -> list[tuple[str, str, dict[str, object]]]:
        rows = AuditEntryRecord.objects.filter(entity_id=entity.value)
        return [(r.action, r.entity_type, r.metadata) for r in rows]

    return DjangoAuditLog(), stored


def test_recorded_entry_keeps_action_entity_and_metadata(
    log_and_store: tuple[AuditLog, Stored],
) -> None:
    log, stored = log_and_store
    entity = Id()
    entry = AuditEntry.from_event(
        actor=Id(),
        action="hospital.updated",
        entity_type="hospital",
        entity_id=entity,
        at=datetime(2026, 11, 20, 10, tzinfo=UTC),
        metadata={"changed": ("name", "city"), "count": 2},
    )

    log.record(entry)

    assert stored(entity) == [
        ("hospital.updated", "hospital", {"changed": ["name", "city"], "count": 2})
    ]


@pytest.mark.integration
@pytest.mark.django_db
def test_django_entry_carries_the_request_correlation_id() -> None:
    entity = Id()
    entry = AuditEntry.from_event(
        actor=None,
        action="auth.login_failed",
        entity_type="user",
        entity_id=entity,
        at=datetime(2026, 11, 20, 10, tzinfo=UTC),
    )

    with structlog.contextvars.bound_contextvars(correlation_id="corr-42"):
        DjangoAuditLog().record(entry)

    assert AuditEntryRecord.objects.get(entity_id=entity.value).correlation_id == "corr-42"
