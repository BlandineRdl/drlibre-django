import dataclasses
from datetime import datetime, timedelta

import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoWaitlist
from drlibre.bootstrap.container import wire
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.integration.bookable import NOW, SLOT_START, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingAppointments(DjangoAppointments):
    def __init__(self, race: Race) -> None:
        self._race = race

    def conflicting_resources(
        self,
        *,
        clinician_id: Id,
        patient_id: Id,
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> tuple[str, ...]:
        # Checked but not yet booked, so without the lock the other writer sees the slot free.
        found = super().conflicting_resources(
            clinician_id=clinician_id,
            patient_id=patient_id,
            start=start,
            end=end,
            excluding=excluding,
        )
        self._race.hold_first()
        return found


def test_an_accept_racing_a_booking_of_its_slot_fails_and_puts_the_entry_back() -> None:
    """Story le patient accepte : un créneau pris entre-temps donne `conflict`, entrée `WAITING`."""
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
            at=NOW,
        )
        DjangoWaitlist().add(entry)
        app.cancel_appointment.execute(
            appointment_id=freed.id, patient_id=leaving.id, reason="Empêchement"
        )
        other = stored_user(Role.PATIENT, password=None)
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, appointments=RacingAppointments(race))
        racing_app = wire(dataclasses.replace(adapters, booking=racing))

        def book() -> object:
            return racing_app.book_appointment.execute(
                patient_id=other.id,
                appointment_type_id=world.scene.kind,
                clinician_id=world.clinician,
                start=SLOT_START,
            )

        def accept() -> object:
            return racing_app.accept_waitlist_offer.execute(actor_id=waiting.id, entry_id=entry.id)

        outcomes = race.run(book, accept)

        assert race.second_was_blocked == [True]
        assert outcomes == ["conflict", "saved"]
        active = AppointmentRecord.objects.filter(
            start=SLOT_START, clinician_id=world.clinician.value
        ).exclude(status=AppointmentStatus.CANCELLED.value)
        assert list(active.values_list("patient_id", flat=True)) == [other.id.value]
        stored = DjangoWaitlist().get(entry.id)
        assert stored is not None
        assert (stored.status, stored.offered_appointment_id) == (WaitlistStatus.WAITING, None)
        lost = AuditEntryRecord.objects.filter(
            action="booking.waitlist_offer_lost", entity_id=entry.id.value
        )
        assert lost.count() == 1
