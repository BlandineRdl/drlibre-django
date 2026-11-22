import dataclasses
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.booking.infrastructure.outbox_notices import OutboxBookingNotices
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import booking_venue, existing_appointment, patient_user
from tests.fakes.world import FakeWorld

START = datetime(2026, 11, 25, 13, 30, tzinfo=UTC)


def reason_appointment(world: FakeWorld) -> Appointment:
    patient, clinician = Id(), Id()
    world.users.save(patient_user(patient))
    world.booking_directory.venues[clinician] = booking_venue("Dr Alice Durand")
    appointment = existing_appointment(
        patient_id=patient, clinician_id=clinician, start=START, end=START + timedelta(minutes=30)
    )
    return dataclasses.replace(appointment, reason="Douleur au genou")


EVENTS: list[tuple[str, Callable[[OutboxBookingNotices, Appointment], object], str, str]] = [
    ("déplacé", OutboxBookingNotices.rescheduled, "RDV déplacé", "Votre rendez-vous est déplacé"),
    ("annulé", OutboxBookingNotices.cancelled, "RDV annulé", "Votre rendez-vous est annulé"),
    ("rappel", OutboxBookingNotices.reminded, "Rappel de RDV", "Rappel de votre rendez-vous"),
]


@pytest.mark.parametrize(
    ("notice", "title", "subject"),
    [pytest.param(n, t, s, id=case) for case, n, t, s in EVENTS],
)
def test_a_changed_appointment_notifies_the_patient_and_emails_time_place_and_provider(
    world: FakeWorld,
    notice: Callable[[OutboxBookingNotices, Appointment], object],
    title: str,
    subject: str,
) -> None:
    """Règle §7.6 : l'email porte l'heure, l'hôpital, le praticien, jamais le motif."""
    appointment = reason_appointment(world)

    notice(world.notices, appointment)

    (notification,) = world.notifications.rows
    assert (notification.title, notification.recipient_id) == (title, appointment.patient_id)
    assert "25/11/2026 à 14:30 (Europe/Paris)" in notification.body
    (mail,) = world.outbox.queued
    assert (mail.to, mail.subject) == (("patient@example.org",), subject)
    for line in ("25/11/2026 à 14:30 (Europe/Paris)", "Hôpital Test", "Dr Alice Durand"):
        assert line in mail.body
    assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]
    assert "Douleur" not in mail.body


def test_a_rescheduled_email_recalls_the_former_date(world: FakeWorld) -> None:
    """Règle §7.6 : l'email de déplacement rappelle l'ancienne date, dans le fuseau nommé."""
    appointment = reason_appointment(world)

    world.notices.rescheduled(appointment, START - timedelta(days=2))

    (mail,) = world.outbox.queued
    assert "Il était prévu le 23/11/2026 à 14:30." in mail.body


def test_an_appointment_already_reminded_is_neither_notified_nor_emailed_again(
    world: FakeWorld,
) -> None:
    """Epic E4 : un RDV n'est rappelé qu'une fois."""
    appointment = reason_appointment(world)

    assert world.notices.reminded(appointment) is True
    assert world.notices.reminded(appointment) is False

    assert len(world.notifications.rows) == 1
    assert len(world.outbox.queued) == 1


def offered_entry(world: FakeWorld) -> tuple[WaitlistEntry, Id]:
    patient, clinician = Id(), Id()
    world.users.save(patient_user(patient))
    world.booking_directory.venues[clinician] = booking_venue("Dr Alice Durand")
    entry = WaitlistEntry.join(
        patient_id=patient,
        appointment_type_id=Id(),
        clinician_id=None,
        earliest=START - timedelta(days=1),
        latest=START + timedelta(days=1),
        at=START - timedelta(days=2),
    )
    return entry.offered(Id()), clinician


def assert_waitlist_email(world: FakeWorld, subject: str) -> None:
    (mail,) = world.outbox.queued
    assert (mail.to, mail.subject) == (("patient@example.org",), subject)
    for line in ("25/11/2026 à 14:30 (Europe/Paris)", "Hôpital Test", "Dr Alice Durand"):
        assert line in mail.body
    assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


def test_an_offered_slot_notifies_the_patient_with_its_time_only_and_emails_it(
    world: FakeWorld,
) -> None:
    """Règle §11 : « Créneau proposé », sans lien vers le RDV d'un autre patient."""
    entry, clinician = offered_entry(world)

    world.notices.waitlist_offered(entry, START, clinician)

    (notification,) = world.notifications.rows
    assert (notification.title, notification.recipient_id) == ("Créneau proposé", entry.patient_id)
    assert notification.body == "Un créneau vous est proposé le 25/11/2026 à 14:30 (Europe/Paris)."
    assert notification.appointment_id is None
    assert_waitlist_email(world, "Un créneau vous est proposé")


def test_a_booked_offer_notifies_the_patient_with_the_new_appointment_and_emails_it(
    world: FakeWorld,
) -> None:
    """Règle §11 : « Créneau réservé » désigne le nouveau RDV, jamais son motif."""
    appointment = reason_appointment(world)

    world.notices.waitlist_booked(appointment)

    (notification,) = world.notifications.rows
    assert (notification.title, notification.appointment_id) == ("Créneau réservé", appointment.id)
    assert notification.body == "Votre créneau du 25/11/2026 à 14:30 (Europe/Paris) est réservé."
    assert_waitlist_email(world, "Votre créneau est réservé")
    assert "Douleur" not in world.outbox.queued[0].body


def test_a_waitlist_notice_rolled_back_with_its_unit_leaves_no_row_and_no_email(
    world: FakeWorld,
) -> None:
    entry, clinician = offered_entry(world)

    def offer_then_fail() -> None:
        with world.uow:
            world.notices.waitlist_offered(entry, START, clinician)
            raise RuntimeError("rolled back")

    with pytest.raises(RuntimeError):
        offer_then_fail()

    assert world.notifications.rows == []
    assert world.outbox.queued == []
