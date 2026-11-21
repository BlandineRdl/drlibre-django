import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../../features/search/chaque_resultat_montre_ses_prochaines_disponibilites.feature")
