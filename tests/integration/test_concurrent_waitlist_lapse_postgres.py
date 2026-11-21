import dataclasses
from datetime import timedelta

import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import DjangoWaitlist
from drlibre.bootstrap.container import wire
from drlibre.identity.domain.user import Role
from tests.builders import stored_user
from tests.integration.bookable import SLOT_START, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingWaitlist(DjangoWaitlist):
    def __init__(self, race: Race) -> None:
        self._race = race

    def save(self, entry: WaitlistEntry) -> None:
        # Booked but not yet saved, so without the lock the job sees the offer still OFFERED.
        self._race.hold_first()
        super().save(entry)


def test_an_offer_accepted_as_its_slot_starts_is_booked_and_never_also_lapsed() -> None:
    """Stories l'admin accepte une offre et une offre non acceptée à temps : jamais les deux."""
    race = Race()
    with bookable() as world:
        app = world.app()
        leaving = stored_user(Role.PATIENT, password=None)
        freed = app.book_appointment.execute(
            patient_id=leaving.id,
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
        )
        waiting = stored_user(Role.PATIENT, password=None)
        entry = WaitlistEntry.join(
            patient_id=waiting.id,
            appointment_type_id=world.scene.kind,
            clinician_id=None,
            earliest=SLOT_START - timedelta(days=1),
            latest=SLOT_START + timedelta(days=1),
            at=SLOT_START - timedelta(days=3),
        )
        DjangoWaitlist().add(entry)
        app.cancel_appointment.execute(
            appointment_id=freed.id, actor_id=leaving.id, reason="Empêchement"
        )
        admin = stored_user(Role.ADMIN)
        # The offered slot starts now: the job lapses it, an admin may still book it.
        adapters = world.at(SLOT_START)
        racing = dataclasses.replace(adapters.booking, waitlist=RacingWaitlist(race))
        racing_app = wire(dataclasses.replace(adapters, booking=racing))

        def accept() -> object:
            return racing_app.accept_waitlist_offer.execute(actor_id=admin.id, entry_id=entry.id)

        outcomes = race.run(accept, racing_app.expire_waitlist.execute)

        assert race.second_was_blocked == [True]
        assert outcomes == ["saved", "saved"]
        active = AppointmentRecord.objects.filter(
            start=SLOT_START, clinician_id=world.clinician.value
        ).exclude(status=AppointmentStatus.CANCELLED.value)
        assert list(active.values_list("patient_id", flat=True)) == [waiting.id.value]
        stored = DjangoWaitlist().get(entry.id)
        assert stored is not None
        assert stored.status is WaitlistStatus.BOOKED
        lapsed = AuditEntryRecord.objects.filter(
            action="booking.waitlist_offer_lapsed", entity_id=entry.id.value
        )
        assert lapsed.count() == 0
