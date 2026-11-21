from datetime import UTC, datetime, timedelta

import pytest
from django.apps import apps

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.bootstrap.container import container
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from drlibre.shared_kernel.ids import Id
from scripts import seed

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def counts() -> dict[str, int]:
    labels = ("identity", "organisation", "scheduling")
    return {
        model.__name__: model._default_manager.count()
        for label in labels
        for model in apps.get_app_config(label).get_models()
    }


def test_the_demo_seed_can_run_again_without_duplicating_rows() -> None:
    """Spec §16: a seed that can be run again without duplicating rows, one sign-in per role."""
    seed.main()
    first = counts()

    seed.main()

    assert counts() == first
    assert first["HospitalRecord"] >= 2
    roles = set(
        UserRecord.objects.filter(email__endswith="@drlibre.localhost").values_list(
            "role", flat=True
        )
    )
    assert roles == {"ADMIN", "CLINICIAN", "PATIENT"}
    admin = UserRecord.objects.get(email="admin@drlibre.localhost")
    seeded = AuditEntryRecord.objects.filter(entity_type="hospital", action="hospital.created")
    assert set(seeded.values_list("actor_id", flat=True)) == {admin.id}


def test_the_demo_clinician_has_free_slots_after_the_seed() -> None:
    """Epic E2: the seeded weekly rules give the demo clinician bookable slots."""
    seed.main()
    consult = AppointmentTypeRecord.objects.get(code="HNORD-CONSULT")
    user = UserRecord.objects.get(email="clinicien@drlibre.localhost")
    profile = container().reference_queries.clinician_profile_of(Id(user.id))
    assert profile is not None
    start = datetime.now(UTC)

    slots = container().find_free_slots.execute(
        appointment_type_id=Id(consult.id),
        clinician_id=profile.id,
        start=start,
        end=start + timedelta(days=7),
    )

    assert slots


def test_the_load_seed_never_double_books_a_room_a_clinician_or_a_patient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec §14 load: seeded appointments respect the placement rules a booking enforces."""
    monkeypatch.setattr(seed, "LOAD_CLINICIANS", 40)
    monkeypatch.setattr(seed, "LOAD_PATIENTS", 400)
    monkeypatch.setattr(seed, "LOAD_APPOINTMENTS_PER_CLINICIAN", 60)

    seed.main(size="load")
    seed.main(size="load")

    rows = list(
        AppointmentRecord.objects.filter(clinician__department__code__startswith="LOAD-").values(
            "patient_id", "clinician_id", "room_id", "start"
        )
    )
    assert len(rows) == 40 * 60
    for key in ("patient_id", "clinician_id", "room_id"):
        slots = [(row[key], row["start"]) for row in rows]
        assert len(set(slots)) == len(slots), key
