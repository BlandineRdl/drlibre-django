import dataclasses

import pytest

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
    VerificationCodeRecord,
)
from drlibre.bootstrap.container import wire
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.scheduling.infrastructure.django.models import SlotModel
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_log import AuditLogUnavailableError
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable, free_starts

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

CONFIRMATION = "Confirmation de votre rendez-vous"


def hold_and_verify(world: Bookable) -> tuple[Id, Id]:
    app = world.app()
    visitor = world.visitor()
    created = app.create_hold.execute(
        appointment_type_id=world.scene.kind,
        clinician_id=world.clinician,
        start=SLOT_START,
        **visitor,  # type: ignore[arg-type]
    )
    done = app.verify_hold.execute(hold_id=created.hold_id, code=world.code(), user_agent="test")
    assert done.appointment is not None
    return created.hold_id, done.appointment.id


def test_a_correct_code_books_the_slot_and_takes_it_off_the_free_slots() -> None:
    """Story réservation : le code correct réserve le créneau et crée le patient."""
    with bookable() as world:
        assert SLOT_START in free_starts(world.app(), world.scene, world.clinician)

        hold_id, appointment_id = hold_and_verify(world)

        booked = AppointmentRecord.objects.get(id=appointment_id.value)
        assert (booked.start, booked.status, booked.source) == (SLOT_START, "BOOKED", "ONLINE")
        assert booked.clinician_id == world.clinician.value
        assert not BookingHoldRecord.objects.filter(id=hold_id.value).exists()
        assert not VerificationCodeRecord.objects.filter(hold_id=hold_id.value).exists()
        assert not SlotModel.objects.filter(
            clinician_id=world.clinician.value,
            start=SLOT_START,
            appointment_type_id=world.scene.kind.value,
        ).exists()
        assert SLOT_START not in free_starts(world.app(), world.scene, world.clinician)
        assert [m.subject for m in world.outbox.queued].count(CONFIRMATION) == 1


def test_the_new_patient_keeps_the_details_of_the_hold_and_the_proof_of_the_email() -> None:
    """Story compte patient : le patient créé porte les informations saisies, email prouvé."""
    with bookable() as world:
        _, appointment_id = hold_and_verify(world)

        patient_id = AppointmentRecord.objects.get(id=appointment_id.value).patient_id
        patient = UserRecord.objects.get(id=patient_id)
        assert patient.role == "PATIENT"
        assert patient.password_hash is None
        assert patient.phone == "0612345678"
        assert str(patient.birth_date) == "1990-05-17"
        assert patient.email_verified_at == NOW


def test_the_booking_and_its_audit_commit_together() -> None:
    """Règle : chaque écriture est auditée dans sa transaction, sans donnée personnelle."""
    with bookable() as world:
        _, appointment_id = hold_and_verify(world)

        actions = AuditEntryRecord.objects.filter(entity_id=appointment_id.value).values_list(
            "action", "metadata"
        )
        (action, metadata) = actions.get()
        assert action == "booking.appointment_booked"
        assert "ana" not in str(metadata).lower()
        assert metadata["email_domain"] == "example.org"
        assert AuditEntryRecord.objects.filter(action="booking.hold_created").exists()


def test_an_audit_failure_leaves_neither_appointment_nor_slot_change() -> None:
    """Règle : un échec d'audit annule la réservation et la mise à jour des créneaux ensemble."""
    with bookable() as world:
        app = world.app()
        created = app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )

        class Failing:
            def record(self, entry: object) -> None:
                raise AuditLogUnavailableError

        adapters = dataclasses.replace(world.at(NOW), audit=Failing())  # type: ignore[arg-type]
        with pytest.raises(AuditLogUnavailableError):
            wire(adapters).verify_hold.execute(
                hold_id=created.hold_id, code=world.code(), user_agent="test"
            )

        assert not AppointmentRecord.objects.exists()
        stored = SlotModel.objects.filter(clinician_id=world.clinician.value, start=SLOT_START)
        assert stored.exists()


def test_an_expired_hold_frees_the_slot_again_without_the_job_running() -> None:
    """Décision du plan : l'expiration d'une garde libère le créneau sans aucun job."""
    with bookable() as world:
        world.app().create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )
        assert SLOT_START not in free_starts(world.app(), world.scene, world.clinician)

        later = NOW.replace(minute=11)

        assert SLOT_START in free_starts(world.app(later), world.scene, world.clinician)
        assert BookingHoldRecord.objects.count() == 1
        assert world.app(later).expire_holds.execute() == 1
        assert BookingHoldRecord.objects.count() == 0


def test_a_type_or_a_clinician_with_appointments_cannot_be_deleted() -> None:
    """Story référentiel : un type ou un praticien ayant des rendez-vous ne se supprime pas."""
    with bookable() as world:
        _, appointment_id = hold_and_verify(world)
        app = world.app()

        with pytest.raises(DomainError) as by_type:
            app.delete_appointment_type.execute(actor=None, record_id=world.scene.kind)
        with pytest.raises(DomainError) as by_profile:
            app.delete_clinician_profile.execute(actor=None, profile_id=world.clinician)

        for refused in (by_type.value, by_profile.value):
            assert refused.code is ErrorCode.HAS_DEPENDENTS
            listed = refused.details["dependents"]
            assert [d["id"] for d in listed] == [str(appointment_id)]
            assert listed[0]["kind"] == "appointment"


def test_a_held_slot_stays_offered_while_another_clinician_still_has_it() -> None:
    """Décision du plan : la recherche retire la garde d'un praticien, pas le créneau des autres."""
    with bookable() as world:
        app = world.app()
        app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )

        assert free_starts(app, world.scene, None).count(SLOT_START) == 1
        assert SLOT_START not in free_starts(app, world.scene, world.clinician)

        app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=world.scene.clinicians[1].id,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )

        assert SLOT_START not in free_starts(app, world.scene, None)
