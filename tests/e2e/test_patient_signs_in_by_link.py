import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages import check_accessible, read_link

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

PASSWORDLESS_PATIENT = "visiteur@drlibre.localhost"


def test_patient_signs_in_by_the_link_received_by_email(page: Page, base_url: str) -> None:
    """Epic E3 : un patient demande un lien, l'ouvre, continue et arrive au portail."""
    page.goto(f"{base_url}/sign-in")
    check_accessible(page)
    page.locator("#field-link_email").fill(PASSWORDLESS_PATIENT)
    page.get_by_role("button", name="Recevoir un lien").click()
    expect(page.get_by_role("heading", name="Vérifiez vos emails")).to_be_visible()
    check_accessible(page)

    page.goto(read_link(PASSWORDLESS_PATIENT))
    expect(page.get_by_role("heading", name="Votre lien de connexion")).to_be_visible()
    check_accessible(page)
    page.get_by_role("button", name="Continuer").click()

    expect(page).to_have_url(f"{base_url}/portal/")
    check_accessible(page)
