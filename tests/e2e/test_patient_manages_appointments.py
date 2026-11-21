from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages import check_accessible, clear_mail, read_code, read_link, read_mail

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

PATIENT = "visiteur@drlibre.localhost"
PATIENT_NAME = "Victor Visiteur"
PROVIDER = "Claire Martin"
BOOKING_REASON = "Palpitations à l'effort"
CANCEL_REASON = "Empêchement professionnel"


def _notified(page: Page, base_url: str, title: str) -> None:
    """The newest notification has this title, without the patient's name or any reason."""
    page.goto(f"{base_url}/portal/notifications")
    newest = page.locator("article.notification").first
    expect(newest.get_by_role("heading")).to_contain_text(title)
    text = page.locator("main").inner_text()
    for secret in (PATIENT_NAME, PROVIDER, BOOKING_REASON, CANCEL_REASON):
        assert secret not in text, f"notification shows {secret!r}"
    check_accessible(page)


def _mailed(subject: str) -> None:
    """The email names no reason and links only to the sign-in page."""
    body = read_mail(PATIENT, subject)
    for leak in (BOOKING_REASON, CANCEL_REASON, "/sign-in/link", "token"):
        assert leak not in body, body
    assert "/sign-in" in body, body


def test_patient_reschedules_then_cancels_and_is_notified_at_each_step(
    page: Page, base_url: str
) -> None:
    """Epic E4 : réservé, déplacé puis annulé, chaque étape notifiée au portail et par email."""
    clear_mail(PATIENT)
    # A week beyond the next one keeps every slot outside the 24-hour cancellation window.
    monday = date.today() + timedelta(days=7 - date.today().weekday() + 7)
    page.goto(f"{base_url}/?q={PROVIDER.replace(' ', '+')}")
    page.get_by_role("link", name=PROVIDER).first.click()
    page.goto(f"{page.url.split('?')[0]}?week={monday.isoformat()}")
    page.locator(".slot-list a").first.click()

    expect(page.get_by_role("heading", name="Vos informations")).to_be_visible()
    page.get_by_label("Nom complet").fill(PATIENT_NAME)
    page.get_by_label("Date de naissance").fill("1990-04-12")
    page.get_by_label("Email").fill(PATIENT)
    page.get_by_label("Motif").fill(BOOKING_REASON)
    page.get_by_label("J'accepte les conditions").check()
    page.get_by_role("button", name="Recevoir un code").click()
    page.get_by_label("Code reçu par email").fill(read_code(PATIENT))
    page.get_by_role("button", name="Réserver").click()
    expect(page.get_by_role("heading", name="Rendez-vous réservé")).to_be_visible()
    calendar = page.get_by_role("button", name="Ajouter à mon agenda (.ics)").get_attribute("href")
    assert calendar, "no calendar link on the confirmation"
    appointment_id = calendar.rsplit("/", 1)[1].removesuffix(".ics")
    _mailed("Confirmation de votre rendez-vous")

    page.context.clear_cookies()
    page.goto(f"{base_url}/sign-in")
    page.locator("#field-link_email").fill(PATIENT)
    page.get_by_role("button", name="Recevoir un lien").click()
    expect(page.get_by_role("heading", name="Vérifiez vos emails")).to_be_visible()
    page.goto(read_link(PATIENT))
    page.get_by_role("button", name="Continuer").click()
    expect(page).to_have_url(f"{base_url}/portal/")
    check_accessible(page)
    _notified(page, base_url, "RDV réservé")

    page.goto(f"{base_url}/portal/appointments")
    card = page.locator(
        "article.appointment-card",
        has=page.locator(f'a[href="/portal/appointments/{appointment_id}.ics"]'),
    )
    when = card.locator(".card-when").inner_text()
    check_accessible(page)
    card.get_by_role("button", name="Déplacer").click()
    expect(page.get_by_role("heading", name="Déplacer le rendez-vous")).to_be_visible()
    check_accessible(page)
    page.get_by_role("link", name="Semaine suivante").click()
    page.locator(".slot-list button").first.click()
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est déplacé.")
    expect(card.locator(".card-when")).not_to_have_text(when)
    _notified(page, base_url, "RDV déplacé")
    _mailed("Votre rendez-vous est déplacé")

    page.goto(f"{base_url}/portal/appointments")
    card.get_by_role("button", name="Annuler").click()
    expect(page.get_by_role("heading", name="Annuler le rendez-vous")).to_be_visible()
    check_accessible(page)
    page.get_by_label("Motif de l'annulation").fill(CANCEL_REASON)
    page.get_by_role("button", name="Confirmer l'annulation").click()
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est annulé.")
    check_accessible(page)
    expect(card.get_by_role("button", name="Annuler")).to_have_count(0)
    _notified(page, base_url, "RDV annulé")
    _mailed("Votre rendez-vous est annulé")

    page.goto(f"{base_url}/portal/profile")
    expect(page.get_by_role("heading", name="Mon profil")).to_be_visible()
    check_accessible(page)
