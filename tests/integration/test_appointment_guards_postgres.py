from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.django.models import AppointmentRecord, BookingHoldRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import StoredScene, existing_appointment, stored_scene

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

START = datetime(2026, 12, 1, 9, tzinfo=UTC)
HALF_HOUR = timedelta(minutes=30)


def booked(
    scene: StoredScene,
    *,
    start: datetime = START,
    patient: Id | None = None,
    clinician: int = 0,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Appointment:
    return existing_appointment(
        patient_id=patient or Id(),
        clinician_id=scene.clinicians[clinician].id,
        appointment_type_id=scene.kind,
        start=start,
        end=start + HALF_HOUR,
        status=status,
    )


def refused_by(constraint: str, **fields: object) -> None:
    with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
        AppointmentRecord.objects.create(**fields)


def test_back_to_back_appointments_of_one_clinician_are_both_kept() -> None:
    """Règle §5.2 : un rendez-vous occupe son créneau, pas le suivant."""
    scene = stored_scene()
    store = DjangoAppointments()
    first = booked(scene)
    store.add(first)
    store.add(booked(scene, start=START + HALF_HOUR))
    cancelled = replace(
        first,
        status=AppointmentStatus.CANCELLED,
        cancelled_at=START - timedelta(days=2),
        cancellation_reason="Empêchement",
    )

    store.save(cancelled)

    assert store.get(first.id) == cancelled
    assert AppointmentRecord.objects.count() == 2


@pytest.mark.parametrize("resource", ["clinician", "patient"])
def test_an_overlapping_active_appointment_is_refused_as_a_conflict(resource: str) -> None:
    """Règle §5.2 : un clinicien ou un patient n'a jamais deux rendez-vous actifs en même temps."""
    scene = stored_scene()
    store = DjangoAppointments()
    patient = Id()
    store.add(booked(scene, patient=patient))
    overlapping = (
        booked(scene, start=START + timedelta(minutes=15))
        if resource == "clinician"
        else booked(scene, start=START + timedelta(minutes=15), patient=patient, clinician=1)
    )

    with pytest.raises(DomainError) as refused:
        store.add(overlapping)

    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.details == {"resources": [resource]}
    assert AppointmentRecord.objects.count() == 1


def test_moving_an_appointment_onto_another_active_one_is_refused_as_a_conflict() -> None:
    """Règle §5.2 : un déplacement ne chevauche pas un autre rendez-vous actif."""
    scene = stored_scene()
    store = DjangoAppointments()
    store.add(booked(scene))
    moved = booked(scene, start=START + timedelta(hours=2))
    store.add(moved)

    with pytest.raises(DomainError) as refused:
        store.save(replace(moved, start=START, end=START + HALF_HOUR))

    assert refused.value.code is ErrorCode.CONFLICT


@pytest.mark.parametrize("status", [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW])
def test_a_cancelled_or_missed_appointment_frees_its_time(status: AppointmentStatus) -> None:
    """Règle §5.2 : seul un rendez-vous actif occupe le créneau."""
    scene = stored_scene()
    store = DjangoAppointments()
    patient = Id()
    store.add(booked(scene, patient=patient, status=status))

    store.add(booked(scene, patient=patient))

    assert AppointmentRecord.objects.count() == 2


@pytest.mark.parametrize("length", [timedelta(0), -HALF_HOUR])
def test_an_appointment_never_ends_before_it_starts(length: timedelta) -> None:
    """Règle §3.1 : la fin d'un rendez-vous suit son début."""
    scene = stored_scene()
    row = booked(scene)
    refused_by(
        "appointment_end_after_start",
        patient_id=row.patient_id.value,
        clinician_id=row.clinician_id.value,
        appointment_type_id=scene.kind.value,
        start=START,
        end=START + length,
        status="BOOKED",
        source="ONLINE",
    )


def test_a_booking_hold_never_ends_before_it_starts() -> None:
    """Règle §3.1 : la fin d'une réservation provisoire suit son début."""
    scene = stored_scene()
    with pytest.raises(IntegrityError, match="booking_hold_end_after_start"), transaction.atomic():
        BookingHoldRecord.objects.create(
            clinician_id=scene.clinicians[0].id.value,
            appointment_type_id=scene.kind.value,
            start=START,
            end=START,
            source="ONLINE",
            full_name="Ana Martin",
            birth_date=date(1990, 5, 17),
            email="ana@example.org",
            expires_at=START,
        )


def test_an_appointment_status_is_one_of_the_five_known() -> None:
    """Règle §3.1 : un rendez-vous porte un des cinq statuts connus."""
    scene = stored_scene()
    refused_by(
        "appointment_status_known",
        patient_id=Id().value,
        clinician_id=scene.clinicians[0].id.value,
        appointment_type_id=scene.kind.value,
        start=START,
        end=START + HALF_HOUR,
        status="PENDING",
        source="ONLINE",
    )


@pytest.mark.parametrize(
    ("status", "cancelled_at", "reason"),
    [
        ("CANCELLED", None, None),
        ("CANCELLED", START, None),
        ("BOOKED", START, "Empêchement"),
        ("BOOKED", None, "Empêchement"),
    ],
)
def test_only_a_cancelled_appointment_carries_its_cancellation_time_and_reason(
    status: str, cancelled_at: datetime | None, reason: str | None
) -> None:
    """Règle §3.1 : un rendez-vous annulé garde l'heure et le motif de son annulation."""
    scene = stored_scene()
    refused_by(
        "appointment_cancellation_consistent",
        patient_id=Id().value,
        clinician_id=scene.clinicians[0].id.value,
        appointment_type_id=scene.kind.value,
        start=START,
        end=START + HALF_HOUR,
        status=status,
        source="ONLINE",
        cancelled_at=cancelled_at,
        cancellation_reason=reason,
    )
