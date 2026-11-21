import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e.pages import check_accessible, clear_mail, read_link, read_mail, sign_in

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

WAITING = "visiteur@drlibre.localhost"
LEAVING = "patient@drlibre.localhost"
ADMIN = "admin@drlibre.localhost"
PROVIDER = "Claire Martin"
TYPE = "Consultation de cardiologie · Hôpital Nord"
CANCEL_REASON = "Déplacement imprévu"
UPCOMING = 'section[aria-labelledby="upcoming-heading"] article.appointment-card'


def _sign_in_by_link(page: Page, base_url: str) -> None:
    page.context.clear_cookies()
    page.goto(f"{base_url}/sign-in")
    page.locator("#field-link_email").fill(WAITING)
    page.get_by_role("button", name="Recevoir un lien").click()
    expect(page.get_by_role("heading", name="Vérifiez vos emails")).to_be_visible()
    page.goto(read_link(WAITING))
    page.get_by_role("button", name="Continuer").click()
    expect(page).to_have_url(f"{base_url}/portal/")


def _cancel(page: Page, marker: Locator) -> None:
    """Cancels the upcoming appointment whose card holds this marker."""
    card = page.locator(UPCOMING, has=marker)
    card.get_by_role("button", name="Annuler").click()
    page.get_by_label("Motif de l'annulation").fill(CANCEL_REASON)
    page.get_by_role("button", name="Confirmer l'annulation").click()
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est annulé.")


def _notified(page: Page, base_url: str, title: str) -> None:
    page.goto(f"{base_url}/portal/notifications")
    expect(page.locator("article.notification").first.get_by_role("heading")).to_contain_text(title)
    assert CANCEL_REASON not in page.locator("main").inner_text()


def _mailed(subject: str) -> None:
    body = read_mail(WAITING, subject)
    for leak in (CANCEL_REASON, "/sign-in/link", "token"):
        assert leak not in body, body
    assert "/sign-in" in body, body


def test_a_cancelled_slot_is_offered_to_the_waiting_patient_who_accepts_it(
    page: Page, base_url: str
) -> None:
    """Epic E5 : un RDV annulé est proposé à l'inscrit en attente, qui l'accepte en RDV `BOOKED`."""
    clear_mail(WAITING)
    # Three weeks ahead keeps the slot outside the 24-hour cancellation window and other journeys.
    monday = date.today() + timedelta(days=7 - date.today().weekday() + 21)

    _sign_in_by_link(page, base_url)
    page.get_by_role("navigation").get_by_role("link", name="Liste d'attente").click()
    expect(page.get_by_role("heading", name="Liste d'attente", level=1)).to_be_visible()
    check_accessible(page)
    page.locator("#field-appointment_type_id").select_option(label=TYPE)
    page.locator("#field-from_date").fill(monday.isoformat())
    page.locator("#field-to_date").fill((monday + timedelta(days=6)).isoformat())
    page.get_by_role("button", name="S'inscrire").click()
    expect(page.get_by_role("status")).to_have_text("Inscription enregistrée.")
    check_accessible(page)

    page.context.clear_cookies()
    sign_in(page, base_url, LEAVING)
    page.goto(f"{base_url}/?q={PROVIDER.replace(' ', '+')}")
    page.get_by_role("link", name=PROVIDER).first.click()
    page.goto(f"{page.url.split('?')[0]}?week={monday.isoformat()}")
    page.locator(".slot-list a").first.click()
    page.get_by_role("button", name="Confirmer le rendez-vous").click()
    expect(page.get_by_role("heading", name="Rendez-vous réservé")).to_be_visible()
    calendar = page.get_by_role("button", name="Ajouter à mon agenda (.ics)").get_attribute("href")
    assert calendar, "no calendar link on the confirmation"
    freed = calendar.rsplit("/", 1)[1].removesuffix(".ics")
    page.goto(f"{base_url}/portal/appointments")
    _cancel(page, page.locator(f'a[href="/portal/appointments/{freed}.ics"]'))

    _sign_in_by_link(page, base_url)
    _notified(page, base_url, "Créneau proposé")
    _mailed("Un créneau vous est proposé")
    page.goto(f"{base_url}/portal/waitlist")
    offered = page.locator(
        "article.appointment-card", has=page.get_by_role("button", name="Accepter")
    )
    expect(offered.first).to_contain_text("Statut : Créneau proposé")
    check_accessible(page)
    when = re.search(r"Proposé : (\S+ \d\d/\d\d/\d{4}) (\d\d:\d\d)", offered.first.inner_text())
    assert when, "no offered time on the card"
    offered.first.get_by_role("button", name="Accepter").click()
    expect(page.get_by_role("status")).to_have_text("Le créneau proposé est réservé.")
    booked = page.get_by_text(f"{when[1]} de {when[2]}")
    expect(page.locator(UPCOMING, has=booked)).to_contain_text("Statut : Réservé")
    _notified(page, base_url, "Créneau réservé")
    _mailed("Votre créneau est réservé")

    page.context.clear_cookies()
    sign_in(page, base_url, ADMIN)
    page.goto(f"{base_url}/console/waitlist/?status=BOOKED")
    expect(page.get_by_role("heading", name="Liste d'attente", level=1)).to_be_visible()
    check_accessible(page)
    page.goto(f"{base_url}/console/waitlist/new")
    check_accessible(page)

    # Free the booked slot again, so the open online bookings never pile up across runs.
    _sign_in_by_link(page, base_url)
    page.goto(f"{base_url}/portal/appointments")
    _cancel(page, page.get_by_text(f"{when[1]} de {when[2]}"))
