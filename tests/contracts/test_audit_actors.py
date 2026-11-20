from datetime import UTC, datetime

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.identity.application.ports.outbound import AuditActors
from drlibre.identity.infrastructure.audit_actors import AuditLogActors
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_actors import InMemoryAuditActors
from tests.fakes.audit_log import InMemoryAuditLog

REAL = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def log_and_actors(request: pytest.FixtureRequest) -> tuple[AuditLog, AuditActors]:
    if request.param == "fake":
        log = InMemoryAuditLog()
        return log, InMemoryAuditActors(log)
    return DjangoAuditLog(), AuditLogActors(DjangoAuditQueries())


def test_a_user_who_acted_in_the_audit_log_is_known_as_an_actor(
    log_and_actors: tuple[AuditLog, AuditActors],
) -> None:
    """Supports: deletion is refused for a user who is the actor of audit entries."""
    log, actors = log_and_actors
    actor, bystander = Id(), Id()
    log.record(
        AuditEntry.from_event(
            actor=actor,
            action="hospital.created",
            entity_type="hospital",
            entity_id=bystander,
            at=datetime(2026, 11, 20, 10, tzinfo=UTC),
        )
    )

    assert actors.has_acted(actor) is True
    assert actors.has_acted(bystander) is False
