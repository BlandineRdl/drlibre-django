from datetime import UTC, datetime

import pytest
from django.db import transaction

from drlibre.notifications.domain.notification import AppointmentEvent, Notification
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.notifications.infrastructure.repositories import DjangoNotifications
from drlibre.shared_kernel.ids import Id
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def test_two_reminder_runs_at_once_leave_a_single_reminder() -> None:
    """Epic E4 : deux passages concurrents du job de rappel ne rappellent un RDV qu'une fois."""
    race, store = Race(), DjangoNotifications()
    patient, appointment = Id(), Id()
    created: list[bool] = []

    def remind() -> None:
        with transaction.atomic():
            created.append(
                store.add(
                    Notification.for_event(
                        event=AppointmentEvent.REMINDED,
                        recipient_id=patient,
                        appointment_id=appointment,
                        start=datetime(2026, 11, 25, 13, 30, tzinfo=UTC),
                        zone_name="Europe/Paris",
                        at=datetime(2026, 11, 24, 13, 30, tzinfo=UTC),
                    )
                )
            )
            # The first run commits only once the second waits on its uncommitted row.
            race.hold_first()

    outcomes = race.run(remind, remind)

    assert race.second_was_blocked == [True]
    assert outcomes == ["saved", "saved"]
    assert created == [True, False]
    assert NotificationRecord.objects.filter(appointment_id=appointment.value).count() == 1
