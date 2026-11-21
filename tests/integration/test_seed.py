from datetime import UTC, datetime, timedelta

import pytest
from django.apps import apps

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
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
