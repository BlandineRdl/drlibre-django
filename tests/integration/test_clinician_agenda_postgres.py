import dataclasses
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import real_adapters, wire
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.builders import unique_email
from tests.builders_booking import existing_appointment, patient_user, stored_scene
from tests.fakes.clock import FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


def test_the_day_follows_the_hospital_zone_around_midnight() -> None:
    """Story « agenda du jour » : les heures sont celles du fuseau de l'hôpital."""
    scene = stored_scene()
    patient = Id()
    DjangoUsers().save(
        dataclasses.replace(
            patient_user(patient, email=unique_email("patient")), full_name="Marie Curie"
        )
    )
    starts = (
        datetime(2026, 11, 19, 22, 30, tzinfo=UTC),
        datetime(2026, 11, 19, 23, 30, tzinfo=UTC),
        datetime(2026, 11, 20, 22, 30, tzinfo=UTC),
        datetime(2026, 11, 20, 23, 30, tzinfo=UTC),
    )
    for start in starts:
        DjangoAppointments().add(
            existing_appointment(
                patient_id=patient,
                clinician_id=scene.clinicians[0].id,
                appointment_type_id=scene.kind,
                start=start,
                end=start + timedelta(minutes=30),
                room_id=scene.room,
                status=AppointmentStatus.BOOKED,
            )
        )

    view = wire(real_adapters(FixedClock(NOW))).clinician_day.execute(
        actor_id=scene.clinicians[0].user_id, day=date(2026, 11, 20)
    )

    assert view.time_zone == "Europe/Paris"
    assert [(h.hour, [e.appointment.start for e in h.entries]) for h in view.hours] == [
        (0, [starts[1]]),
        (23, [starts[2]]),
    ]
