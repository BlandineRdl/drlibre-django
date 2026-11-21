import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios(
    "../../features/search/le_visiteur_consulte_les_pages_publiques_des_praticiens_hopitaux_et_specialites.feature"
)
