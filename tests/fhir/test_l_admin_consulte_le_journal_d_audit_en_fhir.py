import pytest
from pytest_bdd import scenarios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/fhir/l_admin_consulte_le_journal_d_audit_en_fhir.feature")
