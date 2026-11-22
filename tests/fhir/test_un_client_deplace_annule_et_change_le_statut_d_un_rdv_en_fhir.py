import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/fhir/un_client_deplace_annule_et_change_le_statut_d_un_rdv_en_fhir.feature")
