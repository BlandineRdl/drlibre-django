from datetime import timedelta

import pytest
from celery.schedules import crontab

from config.celery import app as celery_app
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
from drlibre.interfaces.jobs.tasks import send_appointment_reminders
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from tests.builders import stored_user
from tests.integration.bookable import SLOT_START, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_the_reminder_job_runs_every_fifteen_minutes_without_an_admin() -> None:
    """Story rappel : le job est exécuté sur planning, sans action d'un admin."""
    entry = celery_app.conf.beat_schedule["send-appointment-reminders"]

    assert entry["task"] == "drlibre.send_appointment_reminders"
    assert entry["schedule"] == crontab(minute="*/15")


def test_two_scheduled_runs_remind_an_appointment_once_by_email_and_audit_once() -> None:
    """Story rappel : deux exécutions ne créent qu'un rappel par RDV, audité par son nombre."""
    with bookable() as world:
        patient = stored_user(Role.PATIENT, password=None)
        appointment = world.app().book_appointment.execute(
            patient_id=patient.id,
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
        )
        # A day before the visit, so it falls inside the reminder window.
        run_at = SLOT_START - timedelta(hours=23)
        use_container(world.app(run_at))
        try:
            counts = [send_appointment_reminders(), send_appointment_reminders()]
        finally:
            use_container(None)

        # Other stored appointments in the window may be reminded too; the second run adds none.
        assert counts[0] >= 1
        assert counts[1] == 0
        reminders = NotificationRecord.objects.filter(
            appointment_id=appointment.id.value, kind="APPOINTMENT_REMINDER"
        )
        assert reminders.count() == 1
        sent = [m for m in world.outbox.queued if m.subject == "Rappel de votre rendez-vous"]
        assert [m.to for m in sent] == [(patient.email.value,)]
        audited = AuditEntryRecord.objects.filter(action="booking.reminders_sent", at=run_at)
        assert list(audited.values_list("metadata", flat=True)) == [{"count": counts[0]}]
