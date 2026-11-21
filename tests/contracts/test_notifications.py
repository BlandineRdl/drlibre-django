import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.notifications.domain.notification import AppointmentEvent, Notification
from drlibre.notifications.infrastructure.repositories import DjangoNotifications
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, PageRequest
from tests.fakes.notifications import InMemoryNotifications

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
START = datetime(2026, 11, 25, 13, 30, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def store(request: pytest.FixtureRequest) -> Notifications:
    return InMemoryNotifications() if request.param == "fake" else DjangoNotifications()


def notice(
    recipient: Id,
    *,
    event: AppointmentEvent = AppointmentEvent.BOOKED,
    appointment: Id | None = None,
    minutes: int = 0,
) -> Notification:
    return Notification.for_event(
        event=event,
        recipient_id=recipient,
        appointment_id=appointment or Id(),
        start=START,
        zone_name="Europe/Paris",
        at=NOW + timedelta(minutes=minutes),
    )


def test_a_stored_notification_is_read_back_unchanged(store: Notifications) -> None:
    notification = notice(Id())

    assert store.add(notification) is True
    assert store.get(notification.id) == notification
    assert store.get(Id()) is None


def test_a_patient_lists_only_their_notifications_newest_first(store: Notifications) -> None:
    """Story notifications : des plus récentes aux plus anciennes, et seulement les siennes."""
    patient, other = Id(), Id()
    older, newer = notice(patient, minutes=1), notice(patient, minutes=2)
    for notification in (older, newer, notice(other, minutes=3)):
        store.add(notification)

    page = store.page_for(patient, PageRequest())

    assert page.items == (newer, older)
    assert page.total == 2


def test_the_list_holds_twenty_notifications_per_page(store: Notifications) -> None:
    patient = Id()
    for minutes in range(PAGE_SIZE + 1):
        store.add(notice(patient, minutes=minutes))

    first, second = store.page_for(patient, PageRequest()), store.page_for(patient, PageRequest(2))

    assert len(first.items) == PAGE_SIZE
    assert [n.created_at for n in second.items] == [NOW]
    assert first.total == PAGE_SIZE + 1


def test_a_read_notification_leaves_the_unread_count(store: Notifications) -> None:
    patient = Id()
    first, second = notice(patient), notice(patient, minutes=1)
    store.add(first)
    store.add(second)

    store.save(first.mark_read(NOW + timedelta(hours=1)))

    assert store.unread_count(patient) == 1
    stored = store.get(first.id)
    assert stored is not None
    assert stored.read_at == NOW + timedelta(hours=1)


def test_marking_an_unknown_notification_is_refused_as_not_found(store: Notifications) -> None:
    with pytest.raises(DomainError) as refused:
        store.save(notice(Id()))

    assert refused.value.code is ErrorCode.NOT_FOUND


def test_an_appointment_is_reminded_only_once(store: Notifications) -> None:
    """Epic E4 : deux passages du job de rappel n'envoient jamais deux rappels."""
    patient, appointment = Id(), Id()
    reminder = notice(patient, event=AppointmentEvent.REMINDED, appointment=appointment)

    assert store.add(reminder) is True
    assert store.add(dataclasses.replace(reminder, id=Id())) is False
    assert store.page_for(patient, PageRequest()).items == (reminder,)


def test_an_appointment_may_change_several_times(store: Notifications) -> None:
    patient, appointment = Id(), Id()

    assert store.add(notice(patient, appointment=appointment)) is True
    assert store.add(
        notice(patient, event=AppointmentEvent.RESCHEDULED, appointment=appointment, minutes=1)
    )
    assert store.page_for(patient, PageRequest()).total == 2


def test_only_appointments_with_a_reminder_are_found_reminded(store: Notifications) -> None:
    patient, reminded, booked, other = Id(), Id(), Id(), Id()
    store.add(notice(patient, event=AppointmentEvent.REMINDED, appointment=reminded))
    store.add(notice(patient, appointment=booked))
    store.add(notice(patient, event=AppointmentEvent.REMINDED, appointment=other))

    assert store.reminded_among(frozenset({reminded, booked})) == {reminded}
    assert store.reminded_among(frozenset()) == frozenset()


@pytest.mark.parametrize(
    "event", [AppointmentEvent.WAITLIST_OFFERED, AppointmentEvent.WAITLIST_BOOKED]
)
def test_a_waitlist_notification_is_stored_with_or_without_its_appointment(
    store: Notifications, event: AppointmentEvent
) -> None:
    """Règle §11 : l'offre ne désigne aucun RDV, la réservation désigne le nouveau RDV."""
    patient = Id()
    unlinked = Notification.for_event(
        event=event,
        recipient_id=patient,
        appointment_id=None,
        start=START,
        zone_name="Europe/Paris",
        at=NOW,
    )
    linked = notice(patient, event=event, minutes=1)

    assert store.add(unlinked) is True
    assert store.add(linked) is True
    assert store.get(unlinked.id) == unlinked
    assert store.page_for(patient, PageRequest()).items == (linked, unlinked)
