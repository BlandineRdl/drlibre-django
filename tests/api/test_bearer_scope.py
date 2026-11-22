import pytest
from django.test import Client

from drlibre.identity.domain.user import Role
from tests.builders import stored_user
from tests.fhir.conftest import token_for

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _bearer(role: Role) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(stored_user(role))}"}


@pytest.mark.parametrize("path", ["/console/", "/console/appointments/export.csv"])
def test_a_bearer_token_opens_no_web_page(path: str) -> None:
    """Spec §2: the bearer token is for the APIs; on a web page its holder is anonymous."""
    response = Client().get(path, headers=_bearer(Role.ADMIN))

    assert response.status_code == 302
    assert response["Location"].startswith("/sign-in?")


def test_a_bearer_token_still_opens_the_api() -> None:
    """INSTALL.md: hashed bearer tokens for API/FHIR."""
    response = Client().get("/api/v1/appointments", headers=_bearer(Role.PATIENT))

    assert response.status_code == 200
