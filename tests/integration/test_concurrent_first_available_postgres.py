import dataclasses
from datetime import timedelta

import pytest
from django.db import OperationalError

from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.booking.infrastructure.schedule_locks import DjangoScheduleLocks
from drlibre.bootstrap.container import wire
from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.django.models import ClinicianProfileRecord
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingLocks(DjangoScheduleLocks):
    def __init__(self, race: Race) -> None:
        self._race = race

    def lock_clinician(self, clinician_id: Id) -> None:
        super().lock_clinician(clinician_id)
        self._race.hold_first()

    def lock_clinicians(self, clinician_ids: tuple[Id, ...]) -> None:
        super().lock_clinicians(clinician_ids)
        self._race.hold_first()


def occupy(world: Bookable, clinician: Id) -> None:
    # Stored without a slot refresh: the slot is still listed, though the clinician is taken.
    kind_minutes = timedelta(minutes=30)
    DjangoAppointments().add(
        Appointment.book(
            patient_id=stored_user(Role.PATIENT, password=None).id,
            clinician_id=clinician,
            appointment_type_id=world.scene.kind,
            room_id=None,
            start=SLOT_START,
            duration=kind_minutes,
            source=Source.STAFF,
        )
    )


def test_two_first_available_bookings_ranking_differently_never_deadlock() -> None:
    """Règle §5.5 : deux gardes du premier disponible au même instant ne s'interbloquent pas."""
    race = Race()
    with bookable() as world:
        first, second = (profile.id for profile in world.scene.clinicians)
        # At NOW the first clinician ranks first; eight days earlier the second does.
        ClinicianProfileRecord.objects.filter(pk=first.value).update(
            weight=3, last_assigned_at=NOW - timedelta(days=10)
        )
        ClinicianProfileRecord.objects.filter(pk=second.value).update(
            weight=1, last_assigned_at=NOW - timedelta(days=20)
        )
        occupy(world, first)
        occupy(world, second)
        errors: list[str] = []
        locks = RacingLocks(race)

        def hold(instant_offset: timedelta):
            visitor = world.visitor()
            adapters = world.at(NOW + instant_offset)
            racing = dataclasses.replace(adapters.booking, locks=locks)
            app = wire(dataclasses.replace(adapters, booking=racing))

            def run() -> object:
                try:
                    return app.create_hold.execute(
                        appointment_type_id=world.scene.kind,
                        clinician_id=None,
                        start=SLOT_START,
                        **visitor,  # type: ignore[arg-type]
                    )
                except OperationalError as error:
                    errors.append(type(error.__cause__).__name__)
                    return None

            return run

        outcomes = race.run(hold(timedelta()), hold(-timedelta(days=8)))

        assert errors == []
        assert race.second_was_blocked == [True]
        assert outcomes == ["no_clinician_available", "no_clinician_available"]
