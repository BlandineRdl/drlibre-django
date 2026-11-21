import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages import check_accessible, read_code

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_visitor_books_a_slot_without_an_account_and_lands_on_their_appointments(
    page: Page, base_url: str
) -> None:
    """Epic E3 : du créneau choisi au portail, sans compte, avec le code reçu par email."""
    email = f"visiteur-{uuid.uuid4().hex[:10]}@example.org"
    page.goto(f"{base_url}/")
    check_accessible(page)
    page.get_by_label("Rechercher un praticien").fill("Claire Martin")
    page.get_by_role("button", name="Rechercher").click()
    page.locator("article .slot-list a").first.click()

    expect(page.get_by_role("heading", name="Vos informations")).to_be_visible()
    check_accessible(page)
    page.get_by_label("Nom complet").fill("Victor Visiteur")
    page.get_by_label("Date de naissance").fill("1990-04-12")
    page.get_by_label("Email").fill(email)
    page.get_by_label("J'accepte les conditions").check()
    page.get_by_role("button", name="Recevoir un code").click()

    expect(page.get_by_role("heading", name="Saisissez votre code")).to_be_visible()
    check_accessible(page)
    page.get_by_label("Code reçu par email").fill(read_code(email))
    page.get_by_role("button", name="Réserver").click()

    expect(page.get_by_role("heading", name="Rendez-vous réservé")).to_be_visible()
    check_accessible(page)
    page.get_by_role("button", name="Voir mes rendez-vous").click()
    expect(page).to_have_url(f"{base_url}/portal/")
    check_accessible(page)


def test_visitor_picks_the_first_available_provider_of_a_specialty(
    page: Page, base_url: str
) -> None:
    """Epic E3 : un créneau d'une spécialité est réservé avec le premier praticien disponible."""
    email = f"visiteur-{uuid.uuid4().hex[:10]}@example.org"
    page.goto(f"{base_url}/?list=specialties&q=Cardiologie")
    page.get_by_text("Filtres").click()
    page.get_by_label("Hôpital").select_option(label="Hôpital Nord")
    page.get_by_role("button", name="Appliquer").click()
    page.locator("article .slot-list a").first.click()

    expect(page.get_by_role("heading", name="Vos informations")).to_be_visible()
    expect(page.get_by_text("Premier praticien disponible")).to_be_visible()
    check_accessible(page)
    page.get_by_label("Nom complet").fill("Fanny Premier")
    page.get_by_label("Date de naissance").fill("1985-02-20")
    page.get_by_label("Email").fill(email)
    page.get_by_label("J'accepte les conditions").check()
    page.get_by_role("button", name="Recevoir un code").click()

    expect(page.get_by_role("heading", name="Saisissez votre code")).to_be_visible()
    check_accessible(page)
    page.get_by_label("Code reçu par email").fill(read_code(email))
    page.get_by_role("button", name="Réserver").click()

    expect(page.get_by_role("heading", name="Rendez-vous réservé")).to_be_visible()
    check_accessible(page)
    # Round robin may pick either demo clinician of the department.
    expect(page.locator("article").first).to_contain_text(re.compile("Claire Martin|Hugo Bernard"))
    expect(page.get_by_text("Premier praticien disponible")).to_have_count(0)
