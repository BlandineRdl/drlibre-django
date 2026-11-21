import dataclasses
from datetime import timedelta

import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.repositories import DjangoWaitlist
from drlibre.bootstrap.container import wire
from drlibre.identity.domain.user import Role
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.integration.bookable import NOW, SLOT_START, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingWaitlist(DjangoWaitlist):
    def __init__(self, race: Race) -> None:
        self._race = race

    def save(self, entry: WaitlistEntry) -> None:
        # Chosen but not yet offered, so without the lock the other cancel sees it WAITING.
        self._race.hold_first()
        super().save(entry)


def test_two_cancellations_at_once_offer_the_oldest_entry_only_once() -> None:
    """Story offre automatique : une seule entrée reçoit l'offre, une seule fois."""
    race = Race()
    with bookable() as world:
        booked: list[Appointment] = []
        # One room only: the two visits follow each other.
        for index, profile in enumerate(world.scene.clinicians):
            patient = stored_user(Role.PATIENT, password=None)
            booked.append(
                world.app().book_appointment.execute(
                    patient_id=patient.id,
                    appointment_type_id=world.scene.kind,
                    clinician_id=profile.id,
                    start=SLOT_START + timedelta(minutes=30 * index),
                )
            )
        waiting = stored_user(Role.PATIENT, password=None)
        entry = WaitlistEntry.join(
            patient_id=waiting.id,
            appointment_type_id=world.scene.kind,
            clinician_id=None,
            earliest=SLOT_START - timedelta(days=1),
            latest=SLOT_START + timedelta(days=1),
            at=NOW,
        )
        DjangoWaitlist().add(entry)
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, waitlist=RacingWaitlist(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def cancel(appointment: Appointment):
            def run() -> object:
                return app.cancel_appointment.execute(
                    appointment_id=appointment.id,
                    actor_id=appointment.patient_id,
                    reason="Empêchement",
                )

            return run

        outcomes = race.run(cancel(booked[0]), cancel(booked[1]))

        assert race.second_was_blocked == [True]
        assert outcomes == ["saved", "saved"]
        stored = DjangoWaitlist().get(entry.id)
        assert stored is not None
        assert stored.status is WaitlistStatus.OFFERED
        assert stored.offered_appointment_id in {booked[0].id, booked[1].id}
        offers = AuditEntryRecord.objects.filter(
            action="booking.waitlist_offered", entity_id=entry.id.value
        )
        assert offers.count() == 1
        notices = NotificationRecord.objects.filter(
            recipient_id=waiting.id.value, kind="WAITLIST_OFFERED"
        )
        assert notices.count() == 1
        assert Id.parse(offers.get().metadata["appointment_id"]) == stored.offered_appointment_id
