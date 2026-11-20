import pytest
from django.test import Client

pytestmark = pytest.mark.usefixtures("fake_container")


def test_cross_origin_post_is_refused_with_forbidden(client: Client) -> None:
    response = client.post("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_cross_site_fetch_metadata_is_refused(client: Client) -> None:
    response = client.post("/sign-in", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == 403
    assert "Accès refusé" in response.content.decode()


@pytest.mark.parametrize(
    "headers", [{"Origin": "http://testserver"}, {}], ids=["same-origin", "no-origin"]
)
def test_same_origin_or_originless_post_passes_through(
    client: Client, headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/health", headers=headers)

    assert response.status_code == 405


def test_unknown_page_renders_the_404_page_in_the_layout(client: Client) -> None:
    response = client.get("/does-not-exist")

    body = response.content.decode()
    assert response.status_code == 404
    assert "Page introuvable" in body
    assert 'lang="fr"' in body
    assert 'href="#main"' in body
