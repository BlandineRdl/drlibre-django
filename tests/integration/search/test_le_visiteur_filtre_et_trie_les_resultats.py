import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../../features/search/le_visiteur_filtre_et_trie_les_resultats.feature")
