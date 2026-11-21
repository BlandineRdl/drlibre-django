from datetime import UTC, datetime, timedelta

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.booking.application.ports.outbound import AppointmentHistory, HistoryEntry
from drlibre.booking.infrastructure.audit_history import AuditAppointmentHistory
from drlibre.shared_kernel.ids import Id
from tests.fakes.appointment_history import InMemoryAppointmentHistory
from tests.fakes.audit_log import InMemoryAuditLog

REAL = [pytest.mark.integration, pytest.mark.django_db]
AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def log_and_history(request: pytest.FixtureRequest) -> tuple[AuditLog, AppointmentHistory]:
    if request.param == "fake":
        log = InMemoryAuditLog()
        return log, InMemoryAppointmentHistory(log)
    return DjangoAuditLog(), AuditAppointmentHistory(DjangoAuditQueries())


def entry(actor: Id | None, action: str, entity_type: str, entity: Id, minutes: int) -> AuditEntry:
    return AuditEntry.from_event(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity,
        at=AT + timedelta(minutes=minutes),
        metadata={"count": 1},
    )


def test_the_history_lists_the_appointments_audit_entries_in_time_order(
    log_and_history: tuple[AuditLog, AppointmentHistory],
) -> None:
    """Story « fiche d'un RDV » : l'historique liste les entrées d'audit dans l'ordre."""
    log, history = log_and_history
    appointment, patient, clinician = Id(), Id(), Id()
    log.record(
        entry(clinician, "booking.appointment_status_changed", "appointment", appointment, 5)
    )
    log.record(entry(patient, "booking.appointment_booked", "appointment", appointment, 1))
    log.record(entry(clinician, "booking.appointment_booked", "appointment", Id(), 2))
    log.record(entry(clinician, "booking.hold_created", "booking_hold", appointment, 3))

    assert history.entries_of(appointment) == (
        HistoryEntry(patient, "booking.appointment_booked", AT + timedelta(minutes=1)),
        HistoryEntry(clinician, "booking.appointment_status_changed", AT + timedelta(minutes=5)),
    )
    assert history.entries_of(Id()) == ()
