import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/fhir/un_client_reserve_et_consulte_des_rdv_en_fhir.feature")
