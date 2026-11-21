import uuid
from datetime import UTC, datetime, timedelta

import pytest
import structlog

from drlibre.audit.application.ports.inbound import AuditFilter, AuditQueries
from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.fakes.audit_log import InMemoryAuditLog
from tests.fakes.audit_queries import InMemoryAuditQueries

REAL = [pytest.mark.integration, pytest.mark.django_db]
AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def journal(request: pytest.FixtureRequest) -> tuple[AuditLog, AuditQueries]:
    if request.param == "fake":
        log = InMemoryAuditLog()
        return log, InMemoryAuditQueries(log)
    return DjangoAuditLog(), DjangoAuditQueries()


def written(log: AuditLog, *, actor: Id | None, entity_type: str, minutes: int) -> str:
    correlation = f"req-{uuid.uuid4().hex[:8]}"
    with structlog.contextvars.bound_contextvars(correlation_id=correlation):
        log.record(
            AuditEntry.from_event(
                actor=actor,
                action=f"{entity_type}.created",
                entity_type=entity_type,
                entity_id=Id(),
                at=AT + timedelta(minutes=minutes),
                metadata={},
            )
        )
    return correlation


def test_the_journal_filters_newest_first_with_its_correlation_ids(
    journal: tuple[AuditLog, AuditQueries],
) -> None:
    """Story L'admin consulte le journal d'audit : filtres, plus récent d'abord, correlation id."""
    log, queries = journal
    actor, other = Id(), Id()
    kind = f"kind_{uuid.uuid4().hex[:8]}"
    first = written(log, actor=actor, entity_type=kind, minutes=0)
    written(log, actor=other, entity_type=kind, minutes=1)
    last = written(log, actor=actor, entity_type=kind, minutes=2)
    written(log, actor=actor, entity_type=f"{kind}_other", minutes=3)

    page = queries.page(AuditFilter(actor_id=actor, entity_type=kind), PageRequest())
    window = queries.page(
        AuditFilter(
            entity_type=kind, start=AT + timedelta(minutes=1), end=AT + timedelta(minutes=2)
        ),
        PageRequest(),
    )

    assert [row.correlation_id for row in page.items] == [last, first]
    assert page.total == 2
    assert [(row.actor_id, row.entity_type) for row in window.items] == [(other, kind)]
    assert {kind, f"{kind}_other"} <= set(queries.entity_types())


def test_an_entry_without_actor_shows_none(journal: tuple[AuditLog, AuditQueries]) -> None:
    """Story L'admin consulte le journal d'audit : acteur vide avant vérification de l'email."""
    log, queries = journal
    kind = f"kind_{uuid.uuid4().hex[:8]}"
    written(log, actor=None, entity_type=kind, minutes=0)

    (row,) = queries.page(AuditFilter(entity_type=kind), PageRequest()).items

    assert (row.actor_id, row.action, row.at) == (None, f"{kind}.created", AT)
    assert row.entity_id is not None
