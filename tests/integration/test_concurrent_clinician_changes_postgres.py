import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from tests.integration.bookable import bookable
from tests.integration.race import Race
from tests.integration.test_concurrent_patient_changes_postgres import booked, racing_app

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def test_a_check_in_racing_a_cancellation_of_one_appointment_changes_it_once() -> None:
    """Story statut : une arrivée sur un RDV annulé entre-temps renvoie `invalid_transition`."""
    race = Race()
    with bookable() as world:
        appointment = booked(world)
        clinician = world.scene.clinicians[0].user_id
        app = racing_app(world, race)

        def cancel() -> object:
            return app.cancel_appointment.execute(
                appointment_id=appointment.id, actor_id=clinician, reason="Urgence au bloc"
            )

        def check_in() -> object:
            return app.check_in_appointment.execute(
                actor_id=clinician, appointment_id=appointment.id
            )

        outcomes = race.run(cancel, check_in)

        assert race.second_was_blocked == [True]
        assert outcomes == ["invalid_transition", "saved"]
        assert AppointmentRecord.objects.get(pk=appointment.id.value).status == "CANCELLED"
        changed = AuditEntryRecord.objects.filter(action="booking.appointment_status_changed")
        assert changed.count() == 0
