import dataclasses
from datetime import datetime, timedelta

import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import Container, wire
from drlibre.identity.domain.user import Role
from drlibre.scheduling.infrastructure.django.models import SlotModel
from tests.builders import stored_user
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingAppointments(DjangoAppointments):
    def __init__(self, race: Race) -> None:
        self._race = race

    def save(self, appointment: Appointment) -> None:
        # Checked but not yet saved, so without the locks the other writer sees a stale row.
        self._race.hold_first()
        super().save(appointment)


def racing_app(world: Bookable, race: Race) -> Container:
    adapters = world.at(NOW)
    racing = dataclasses.replace(adapters.booking, appointments=RacingAppointments(race))
    return wire(dataclasses.replace(adapters, booking=racing))


def booked(world: Bookable, start: datetime = SLOT_START) -> Appointment:
    patient = stored_user(Role.PATIENT, password=None)
    return world.app().book_appointment.execute(
        patient_id=patient.id,
        appointment_type_id=world.scene.kind,
        clinician_id=world.clinician,
        start=start,
    )


def test_two_patients_moving_to_one_slot_at_once_get_it_once() -> None:
    """Story déplacement : un créneau pris pendant le déplacement donne `conflict`."""
    race = Race()
    with bookable() as world:
        first, second = booked(world), booked(world, SLOT_START + timedelta(minutes=30))
        app = racing_app(world, race)
        target = SLOT_START + timedelta(hours=2)

        def move(appointment: Appointment):
            def run() -> object:
                return app.reschedule_appointment.execute(
                    appointment_id=appointment.id, patient_id=appointment.patient_id, start=target
                )

            return run

        outcomes = race.run(move(first), move(second))

        assert race.second_was_blocked == [True]
        assert outcomes == ["conflict", "saved"]
        assert AppointmentRecord.objects.filter(start=target).count() == 1


def test_two_cancellations_of_one_appointment_at_once_cancel_it_once() -> None:
    """Story annulation : une seconde annulation voit le RDV déjà annulé, `invalid_transition`."""
    race = Race()
    with bookable() as world:
        appointment = booked(world)
        app = racing_app(world, race)

        def cancel() -> object:
            return app.cancel_appointment.execute(
                appointment_id=appointment.id, patient_id=appointment.patient_id, reason="Absent"
            )

        outcomes = race.run(cancel, cancel)

        assert race.second_was_blocked == [True]
        assert outcomes == ["invalid_transition", "saved"]
        cancelled = AuditEntryRecord.objects.filter(action="booking.appointment_cancelled")
        assert cancelled.count() == 1


def test_a_move_overlapping_its_own_time_is_accepted_and_frees_the_old_slot() -> None:
    """Story déplacement : le RDV déplacé est ignoré ; ses créneaux sont recalculés."""
    with bookable(duration_minutes=60) as world:
        appointment = booked(world)
        later = SLOT_START + timedelta(minutes=30)

        moved = world.app().reschedule_appointment.execute(
            appointment_id=appointment.id, patient_id=appointment.patient_id, start=later
        )

        assert (moved.start, moved.end) == (later, later + timedelta(hours=1))
        assert moved.status is AppointmentStatus.BOOKED
        starts = SlotModel.objects.filter(
            clinician_id=world.clinician.value, start__lt=SLOT_START + timedelta(days=1)
        )
        assert list(starts.order_by("start").values_list("start", flat=True)) == [
            SLOT_START + timedelta(hours=1, minutes=30),
            SLOT_START + timedelta(hours=2),
        ]
