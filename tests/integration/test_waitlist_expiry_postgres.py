from datetime import timedelta

import pytest

from config.celery import app as celery_app
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoWaitlist
from drlibre.bootstrap.container import use_container
from drlibre.interfaces.jobs.tasks import expire_waitlist
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment
from tests.integration.bookable import NOW, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_the_waitlist_expiry_job_runs_every_minute_without_an_admin() -> None:
    """Story expiration : le job est exécuté sur planning, sans action d'un admin."""
    entry = celery_app.conf.beat_schedule["expire-waitlist"]

    assert entry["task"] == "drlibre.expire_waitlist"
    assert entry["schedule"] == 60.0


def test_two_scheduled_runs_expire_past_entries_and_free_started_offers_once() -> None:
    """Stories expiration et offre échue : chaque entrée échue change une fois, auditée."""
    with bookable() as world:
        kind, clinician = world.scene.kind, world.clinician
        started = existing_appointment(
            patient_id=Id(),
            clinician_id=clinician,
            appointment_type_id=kind,
            start=NOW - timedelta(minutes=30),
            end=NOW,
            status=AppointmentStatus.CANCELLED,
        )
        DjangoAppointments().add(started)

        def entry(latest_in: timedelta) -> WaitlistEntry:
            joined = WaitlistEntry.join(
                patient_id=Id(),
                appointment_type_id=kind,
                clinician_id=None,
                earliest=NOW - timedelta(days=2),
                latest=NOW + latest_in,
                at=NOW - timedelta(days=3),
            )
            DjangoWaitlist().add(joined)
            return joined

        past, future = entry(timedelta()), entry(timedelta(days=1))
        lapsed = entry(timedelta(days=1)).offered(started.id)
        DjangoWaitlist().save(lapsed)
        use_container(world.app(NOW))
        try:
            counts = [expire_waitlist(), expire_waitlist()]
        finally:
            use_container(None)

        assert counts[0] >= 2
        assert counts[1] == 0
        statuses = {e.id: DjangoWaitlist().get(e.id) for e in (past, future, lapsed)}
        assert {i: e.status for i, e in statuses.items() if e} == {
            past.id: WaitlistStatus.EXPIRED,
            future.id: WaitlistStatus.WAITING,
            lapsed.id: WaitlistStatus.WAITING,
        }
        audited = AuditEntryRecord.objects.filter(entity_id__in=[past.id.value, lapsed.id.value])
        assert sorted(audited.values_list("action", "actor_id", "metadata")) == [
            ("booking.waitlist_expired", None, {"status": "EXPIRED"}),
            ("booking.waitlist_offer_lapsed", None, {"status": "WAITING"}),
        ]
