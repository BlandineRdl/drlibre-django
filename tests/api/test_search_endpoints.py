import dataclasses

import pytest
from django.test import Client

from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.repositories import DjangoAppointmentTypes
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_scheduling import stored_department, stored_profile

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

LISTS = ("providers", "hospitals", "specialties")


@pytest.mark.parametrize("kind", LISTS)
def test_anonymous_searches_answer_with_a_page(client: Client, kind: str) -> None:
    """Story recherche : les trois listes répondent sans session."""
    response = client.get(f"/api/v1/search/{kind}")

    assert response.status_code == 200
    assert {"items", "total", "page", "pages", "size"} <= set(response.json())


@pytest.mark.parametrize("kind", LISTS)
def test_an_unusable_filter_value_falls_back_to_its_default(client: Client, kind: str) -> None:
    """Story recherche : une valeur inutilisable retombe sur sa valeur par défaut."""
    query = "size=7&page=x&sort=distance&window=jamais&moment=nuit&specialty=non&from=hier"

    response = client.get(f"/api/v1/search/{kind}?{query}")

    assert response.status_code == 200
    assert (response.json()["size"], response.json()["page"]) == (20, 1)


def test_a_provider_without_an_online_type_is_not_listed_and_has_no_page(client: Client) -> None:
    """Story pages publiques : un praticien sans type réservable en ligne est introuvable."""
    department = stored_department()
    profile = stored_profile(department)

    listed = client.get("/api/v1/search/providers").json()["items"]
    detail = client.get(f"/api/v1/providers/{profile.id}")

    assert str(profile.id) not in [item["id"] for item in listed]
    assert detail.status_code == 404
    assert detail.json()["code"] == "not_found"


def test_a_bookable_provider_has_a_public_page_without_private_data(client: Client) -> None:
    """Story pages publiques : le détail public ne montre ni email ni téléphone."""
    department = stored_department()
    kind = dataclasses.replace(build.appointment_type(department.id), bookable_online=True)
    DjangoAppointmentTypes().save(kind)
    profile = stored_profile(department, user_id=stored_user(Role.CLINICIAN).id)

    response = client.get(f"/api/v1/providers/{profile.id}")

    assert response.status_code == 200
    assert not {"email", "phone", "birth_date"} & set(response.json())
