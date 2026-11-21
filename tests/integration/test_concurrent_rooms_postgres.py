import dataclasses
from datetime import datetime

import pytest

from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments
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

    def busy_rooms(
        self,
        room_ids: tuple[Id, ...],
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> frozenset[Id]:
        # Read before booking, so without the room lock both clinicians see the room free.
        found = super().busy_rooms(room_ids, start, end, excluding)
        self._race.hold_first()
        return found


def test_two_clinicians_of_one_department_never_get_the_same_room_at_once() -> None:
    """Règle §5.2 : une salle n'accueille qu'un rendez-vous à la fois, même en même temps."""
    race = Race()
    with bookable() as world:
        first_clinician, second_clinician = (profile.id for profile in world.scene.clinicians)
        first_patient = stored_user(Role.PATIENT, password=None)
        second_patient = stored_user(Role.PATIENT, password=None)
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, appointments=RacingAppointments(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def book(patient: Id, clinician: Id):
            def run() -> object:
                return app.book_appointment.execute(
                    patient_id=patient,
                    appointment_type_id=world.scene.kind,
                    clinician_id=clinician,
                    start=SLOT_START,
                )

            return run

        outcomes = race.run(
            book(first_patient.id, first_clinician), book(second_patient.id, second_clinician)
        )

        assert race.second_was_blocked == [True]
        assert outcomes == ["no_room_available", "saved"]
        rooms = AppointmentRecord.objects.values_list("room_id", flat=True)
        assert list(rooms) == [world.scene.room.value]
