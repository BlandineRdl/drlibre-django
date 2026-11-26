import dataclasses
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.infrastructure.clinician_agenda import SqlClinicianAgenda
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoHolds
from drlibre.bootstrap.container import real_adapters, wire
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.scheduling.application.ports.outbound import StoredSlot
from drlibre.scheduling.domain.slot import Slot
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
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


def _store_slots(clinician: Id, kind: Id, starts: tuple[datetime, ...]) -> None:
    rows = tuple(StoredSlot(clinician, kind, Slot(s, s + timedelta(minutes=30))) for s in starts)
    DjangoSlotStore().replace(clinician, rows)


def test_the_next_free_slot_leaves_the_buffer_after_a_hold() -> None:
    """Story « agenda du jour » : le prochain créneau libre est réservable, marge comprise."""
    scene = stored_scene(buffer_minutes=10)
    clinician = scene.clinicians[0].id
    held = NOW + timedelta(hours=1)
    in_buffer, free = held + timedelta(minutes=30), held + timedelta(minutes=60)
    _store_slots(clinician, scene.kind, (in_buffer, free))
    details = VisitorDetails(
        full_name="Ana Martin",
        birth_date=date(1990, 1, 1),
        email=unique_email("ana"),
        phone=None,
        reason=None,
    )
    DjangoHolds().add(
        BookingHold.open(
            clinician_id=clinician,
            appointment_type_id=scene.kind,
            start=held,
            duration=timedelta(minutes=30),
            source=Source.ONLINE,
            details=details,
            at=NOW,
        )
    )

    assert SqlClinicianAgenda().next_free_slot(clinician, NOW, NOW) == free


def test_the_next_free_slot_needs_a_free_room() -> None:
    """Story « agenda du jour » : un créneau dont la seule salle est prise n'est pas libre."""
    scene = stored_scene()
    clinician, colleague = scene.clinicians[0].id, scene.clinicians[1].id
    taken, free = NOW + timedelta(hours=1), NOW + timedelta(hours=2)
    _store_slots(clinician, scene.kind, (taken, free))
    patient = Id()
    DjangoUsers().save(patient_user(patient, email=unique_email("patient")))
    DjangoAppointments().add(
        existing_appointment(
            patient_id=patient,
            clinician_id=colleague,
            appointment_type_id=scene.kind,
            start=taken,
            end=taken + timedelta(minutes=30),
            room_id=scene.room,
            status=AppointmentStatus.BOOKED,
        )
    )

    assert SqlClinicianAgenda().next_free_slot(clinician, NOW, NOW) == free
