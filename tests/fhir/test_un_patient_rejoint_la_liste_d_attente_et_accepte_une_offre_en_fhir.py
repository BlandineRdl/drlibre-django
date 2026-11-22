import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios(
    "../features/fhir/un_patient_rejoint_la_liste_d_attente_et_accepte_une_offre_en_fhir.feature"
)
