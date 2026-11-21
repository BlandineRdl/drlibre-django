import dataclasses
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.domain.appointment import Appointment
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


def test_an_appointment_already_reminded_is_neither_notified_nor_emailed_again(
    world: FakeWorld,
) -> None:
    """Epic E4 : un RDV n'est rappelé qu'une fois."""
    appointment = reason_appointment(world)

    assert world.notices.reminded(appointment) is True
    assert world.notices.reminded(appointment) is False

    assert len(world.notifications.rows) == 1
    assert len(world.outbox.queued) == 1
