import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/fhir/le_praticien_gere_ses_disponibilites_en_fhir.feature")
