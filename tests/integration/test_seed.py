import pytest
from django.apps import apps

from drlibre.identity.infrastructure.django.models import UserRecord
from scripts import seed

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def counts() -> dict[str, int]:
    labels = ("identity", "organisation")
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
