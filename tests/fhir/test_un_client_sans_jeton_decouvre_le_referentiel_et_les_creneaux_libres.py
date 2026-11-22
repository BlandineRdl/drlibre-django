import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios(
    "../features/fhir/un_client_sans_jeton_decouvre_le_referentiel_et_les_creneaux_libres.feature"
)
