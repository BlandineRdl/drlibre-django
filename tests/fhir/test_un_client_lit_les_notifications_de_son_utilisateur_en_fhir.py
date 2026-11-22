import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/fhir/un_client_lit_les_notifications_de_son_utilisateur_en_fhir.feature")
