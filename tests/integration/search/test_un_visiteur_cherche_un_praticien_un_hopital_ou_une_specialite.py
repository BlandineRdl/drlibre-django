import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios(
    "../../features/search/un_visiteur_cherche_un_praticien_un_hopital_ou_une_specialite.feature"
)
