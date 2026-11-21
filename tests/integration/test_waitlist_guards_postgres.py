from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.booking.infrastructure.django.models import WaitlistEntryRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoWaitlist
from drlibre.bootstrap.container import real_adapters, wire
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_booking import StoredScene, existing_appointment, stored_scene

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

START = datetime(2026, 12, 1, 9, tzinfo=UTC)
WEEK = timedelta(days=7)


def freed(scene: StoredScene) -> Id:
    appointment = existing_appointment(
        patient_id=Id(),
        clinician_id=scene.clinicians[0].id,
        appointment_type_id=scene.kind,
        start=START + timedelta(days=1),
        end=START + timedelta(days=1, minutes=30),
        status=AppointmentStatus.CANCELLED,
    )
    DjangoAppointments().add(appointment)
    return appointment.id


def row(scene: StoredScene, **changes: Any) -> dict[str, Any]:
    return {
        "patient_id": Id().value,
        "appointment_type_id": scene.kind.value,
        "earliest": START,
        "latest": START + WEEK,
        "status": "WAITING",
        "created_at": START,
        **changes,
    }


def refused_by(constraint: str, fields: dict[str, Any]) -> None:
    with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
        WaitlistEntryRecord.objects.create(**fields)


def test_two_open_offers_of_one_appointment_are_refused_by_the_database() -> None:
    """Décision du plan : un RDV libéré n'est proposé qu'à une entrée à la fois."""
    scene = stored_scene()
    appointment = freed(scene)
    WaitlistEntryRecord.objects.create(
        **row(scene, status="OFFERED", offered_appointment_id=appointment.value)
    )
    refused_by(
        "waitlist_one_offer_per_appointment",
        row(scene, status="OFFERED", offered_appointment_id=appointment.value),
    )


def test_a_second_offer_through_the_adapter_becomes_a_conflict() -> None:
    scene = stored_scene()
    appointment = freed(scene)
    store = DjangoWaitlist()
    first, second = (
        WaitlistEntry.join(
            patient_id=Id(),
            appointment_type_id=scene.kind,
            clinician_id=None,
            earliest=START,
            latest=START + WEEK,
            at=START,
        )
        for _ in range(2)
    )
    store.add(first)
    store.add(second)
    store.save(first.offered(appointment))

    with pytest.raises(DomainError) as refused:
        store.save(second.offered(appointment))

    assert refused.value.code is ErrorCode.CONFLICT


@pytest.mark.parametrize("length", [timedelta(0), -WEEK])
def test_a_waitlist_window_never_ends_before_it_starts(length: timedelta) -> None:
    """Règle §3.1 : la fin de la fenêtre d'attente suit son début."""
    scene = stored_scene()
    refused_by("waitlist_latest_after_earliest", row(scene, latest=START + length))


def test_a_waitlist_status_is_one_of_the_four_known() -> None:
    """Règle §3.1 : une entrée porte un des quatre statuts connus."""
    refused_by("waitlist_status_known", row(stored_scene(), status="PENDING"))


@pytest.mark.parametrize("status", ["OFFERED", "WAITING", "BOOKED", "EXPIRED"])
def test_only_an_offered_entry_points_at_its_offered_appointment(status: str) -> None:
    """Règle §3.1 : seule une entrée OFFERED désigne le RDV proposé."""
    scene = stored_scene()
    offered = None if status == "OFFERED" else freed(scene).value
    refused_by(
        "waitlist_offer_iff_offered", row(scene, status=status, offered_appointment_id=offered)
    )


def test_a_type_clinician_or_patient_with_a_waitlist_entry_is_not_deleted() -> None:
    """Story : un type de RDV qui a des entrées d'attente ne peut pas être supprimé."""
    scene = stored_scene()
    admin = stored_user(Role.ADMIN)
    patient = stored_user(Role.PATIENT)
    profile = scene.clinicians[0]
    entry = WaitlistEntry.join(
        patient_id=patient.id,
        appointment_type_id=scene.kind,
        clinician_id=profile.id,
        earliest=START,
        latest=START + WEEK,
        at=START,
    )
    DjangoWaitlist().add(entry)
    app = wire(real_adapters())
    listed = [{"kind": "waitlist_entry", "id": str(entry.id), "label": "Attente du 01/12/2026"}]

    for delete in (
        lambda: app.delete_appointment_type.execute(actor=admin.id, record_id=scene.kind),
        lambda: app.delete_clinician_profile.execute(actor=admin.id, profile_id=profile.id),
        lambda: app.delete_user.execute(actor=admin.id, user_id=patient.id),
    ):
        with pytest.raises(DomainError) as refused:
            delete()
        assert refused.value.code is ErrorCode.HAS_DEPENDENTS
        assert refused.value.details["dependents"] == listed
