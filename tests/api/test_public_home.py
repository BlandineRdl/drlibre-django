import pytest
from django.test import Client

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_the_home_page_is_the_search_for_anyone_and_offers_sign_in(client: Client) -> None:
    """Story recherche : la page d'accueil est la recherche, sans session."""
    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/sign-in"' in response.content.decode()


def test_a_signed_in_user_keeps_a_link_to_their_space(admin_client: Client) -> None:
    """Décision E3 : `/` est la recherche pour tous ; la navigation garde « Mon espace »."""
    response = admin_client.get("/")

    assert response.status_code == 200
    assert 'href="/console/">Mon espace' in response.content.decode()
