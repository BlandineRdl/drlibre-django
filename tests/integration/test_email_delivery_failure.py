import dataclasses
import smtplib

import pytest
from celery.result import EagerResult

from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
)
from drlibre.bootstrap.container import use_container
from drlibre.interfaces.jobs.tasks import send_email
from drlibre.notifications.application.ports.outbound import EmailMessage, Mailer
from tests.integration.bookable import SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

# The first attempt plus the five retries the task allows.
ATTEMPTS = 6


class DownMailer(Mailer):
    def __init__(self) -> None:
        self.attempts = 0

    def send(self, message: EmailMessage) -> None:
        self.attempts += 1
        raise smtplib.SMTPServerDisconnected


def deliver_all(world: Bookable, mailer: DownMailer) -> list[EagerResult]:
    """Run every queued email through the worker task, with the mail server down."""
    use_container(dataclasses.replace(world.app(), mailer=mailer))
    return [
        send_email.apply(  # pyrefly: ignore[not-callable]
            kwargs={"to": list(m.to), "subject": m.subject, "body": m.body}
        )
        for m in world.outbox.queued
    ]


def test_a_failed_send_is_retried_five_times_before_it_gives_up() -> None:
    """Story réservation par code : les emails partent avec nouvelles tentatives."""
    mailer = DownMailer()
    with bookable() as world:
        use_container(dataclasses.replace(world.app(), mailer=mailer))

        result = send_email.apply(  # pyrefly: ignore[not-callable]
            kwargs={"to": ["a@example.org"], "subject": "s", "body": "b"}
        )

    assert mailer.attempts == ATTEMPTS
    assert result.failed()


def test_a_failed_code_email_keeps_the_hold_and_lets_the_visitor_ask_for_a_new_code() -> None:
    """Story réservation par code : un échec d'envoi n'annule pas la réservation provisoire."""
    with bookable() as world:
        app = world.app()
        created = app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )
        mailer = DownMailer()

        results = deliver_all(world, mailer)

        assert all(r.failed() for r in results)
        assert mailer.attempts == ATTEMPTS * len(results)
        assert BookingHoldRecord.objects.filter(id=created.hold_id.value).exists()
        app.resend_code.execute(hold_id=created.hold_id, network="203.0.113.7")
        assert [m.subject for m in world.outbox.queued].count("Votre code de vérification") == 2


def test_a_failed_confirmation_email_keeps_the_appointment() -> None:
    """Story réservation par code : un échec d'envoi n'annule pas le RDV."""
    with bookable() as world:
        app = world.app()
        created = app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )
        done = app.verify_hold.execute(hold_id=created.hold_id, code=world.code(), user_agent="t")
        assert done.appointment is not None

        deliver_all(world, DownMailer())

        booked = AppointmentRecord.objects.get(id=done.appointment.id.value)
        assert booked.status == "BOOKED"
