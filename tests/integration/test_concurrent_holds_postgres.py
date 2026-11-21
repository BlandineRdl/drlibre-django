import dataclasses
from datetime import datetime

import pytest

from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.infrastructure.django.models import BookingHoldRecord
from drlibre.booking.infrastructure.repositories import DjangoHolds
from drlibre.bootstrap.container import wire
from drlibre.shared_kernel.ids import Id
from tests.integration.bookable import NOW, SLOT_START, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingHolds(DjangoHolds):
    def __init__(self, race: Race) -> None:
        self._race = race

    def held(
        self,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        *,
        at: datetime,
        excluding: Id | None,
    ) -> bool:
        # Read before holding, so without the clinician lock both writers miss each other.
        found = super().held(clinician_id, start, end, at=at, excluding=excluding)
        self._race.hold_first()
        return found


class EmailRacingHolds(DjangoHolds):
    def __init__(self, race: Race) -> None:
        self._race = race

    def open_for_email(self, email: str, at: datetime) -> BookingHold | None:
        # Read before writing, so without the email lock both writers miss each other's hold.
        found = super().open_for_email(email, at)
        self._race.hold_first()
        return found


def test_two_visitors_holding_the_same_slot_at_once_leave_only_one_hold() -> None:
    """Story réservation provisoire : un créneau gardé n'est plus proposé, même au même instant."""
    race = Race()
    with bookable() as world:
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, holds=RacingHolds(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def hold() -> object:
            return app.create_hold.execute(
                appointment_type_id=world.scene.kind,
                clinician_id=world.clinician,
                start=SLOT_START,
                **world.visitor(),  # type: ignore[arg-type]
            )

        outcomes = race.run(hold, hold)

        assert race.second_was_blocked == [True]
        assert outcomes == ["conflict", "saved"]
        assert BookingHoldRecord.objects.filter(clinician_id=world.clinician.value).count() == 1


def test_a_hold_replaces_the_previous_hold_of_the_same_email() -> None:
    """Décision du plan : une seconde garde du même email remplace la première."""
    with bookable() as world:
        visitor = world.visitor()
        app = world.app()

        def hold(start: datetime) -> BookingHold | object:
            return app.create_hold.execute(
                appointment_type_id=world.scene.kind,
                clinician_id=world.clinician,
                start=start,
                **visitor,  # type: ignore[arg-type]
            )

        first = hold(SLOT_START)
        second = hold(SLOT_START.replace(hour=9))

        assert first != second
        assert list(BookingHoldRecord.objects.values_list("start", flat=True)) == [
            SLOT_START.replace(hour=9)
        ]


def test_two_holds_of_one_email_at_once_never_leave_two_open() -> None:
    """Story réservation provisoire : un email n'a jamais plus d'une réservation ouverte."""
    race = Race()
    with bookable() as world:
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, holds=EmailRacingHolds(race))
        app = wire(dataclasses.replace(adapters, booking=racing))
        visitor = world.visitor()

        def hold(start: datetime):
            def run() -> object:
                return app.create_hold.execute(
                    appointment_type_id=world.scene.kind,
                    clinician_id=world.clinician,
                    start=start,
                    **visitor,  # type: ignore[arg-type]
                )

            return run

        outcomes = race.run(hold(SLOT_START), hold(SLOT_START.replace(hour=9)))

        assert race.second_was_blocked == [True]
        assert outcomes == ["saved", "saved"]
        assert BookingHoldRecord.objects.filter(email=visitor["email"]).count() == 1
