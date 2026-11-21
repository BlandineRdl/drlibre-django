"""Spec 1: every write is recorded in an append-only audit log, enforced by PostgreSQL itself."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from django.db import DatabaseError, connection, transaction

from drlibre.audit.infrastructure.django.models import AuditEntryRecord

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def stored_entry() -> AuditEntryRecord:
    return AuditEntryRecord.objects.create(
        action="hospital.created",
        entity_type="hospital",
        at=datetime(2026, 11, 21, 10, tzinfo=UTC),
    )


def raw(sql: str, entry: AuditEntryRecord) -> Callable[[], None]:
    def run() -> None:
        with connection.cursor() as cursor:
            cursor.execute(sql, [entry.pk])

    return run


def refused(write: Callable[[], object]) -> None:
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        write()


def test_a_new_audit_entry_is_recorded() -> None:
    entry = stored_entry()

    assert AuditEntryRecord.objects.filter(pk=entry.pk).exists()


def test_a_bulk_update_never_changes_an_audit_entry() -> None:
    entry = stored_entry()

    refused(lambda: AuditEntryRecord.objects.filter(pk=entry.pk).update(action="forged"))

    assert AuditEntryRecord.objects.get(pk=entry.pk).action == "hospital.created"


def test_a_bulk_delete_never_removes_an_audit_entry() -> None:
    entry = stored_entry()

    refused(lambda: AuditEntryRecord.objects.filter(pk=entry.pk).delete())

    assert AuditEntryRecord.objects.filter(pk=entry.pk).exists()


def test_raw_sql_never_changes_an_audit_entry() -> None:
    entry = stored_entry()

    refused(raw("UPDATE audit_auditentryrecord SET action = 'forged' WHERE id = %s", entry))

    assert AuditEntryRecord.objects.get(pk=entry.pk).action == "hospital.created"


def test_raw_sql_never_removes_an_audit_entry() -> None:
    entry = stored_entry()

    refused(raw("DELETE FROM audit_auditentryrecord WHERE id = %s", entry))

    assert AuditEntryRecord.objects.filter(pk=entry.pk).exists()


def test_emptying_the_audit_log_is_refused() -> None:
    entry = stored_entry()
    with connection.cursor() as cursor:
        # The test database lets flushes truncate; this test's transaction restores the guard.
        cursor.execute(
            "ALTER TABLE audit_auditentryrecord ENABLE TRIGGER audit_entries_never_truncated"
        )

    refused(lambda: connection.cursor().execute("TRUNCATE audit_auditentryrecord"))

    assert AuditEntryRecord.objects.filter(pk=entry.pk).exists()
