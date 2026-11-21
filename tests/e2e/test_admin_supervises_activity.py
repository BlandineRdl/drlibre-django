import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages import check_accessible, sign_in

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

ADMIN = "admin@drlibre.localhost"
PATIENT = "Paul Patient"
STAFF_TYPE = "Échocardiographie · Hôpital Nord"
PROVIDER = "Hugo Bernard · Cardiologie"
CANCEL_REASON = "Examen reporté"


def _book_for_patient(page: Page, base_url: str) -> str:
    """Books the staff-only type for the patient, returns the new appointment's file url."""
    page.goto(f"{base_url}/console/appointments/")
    page.get_by_role("button", name="Réserver pour un patient").click()
    expect(page.get_by_role("heading", name="Réserver pour un patient", level=1)).to_be_visible()
    check_accessible(page)
    page.get_by_label("Nom ou email du patient").fill(PATIENT)
    page.get_by_role("button", name="Chercher").click()
    page.get_by_label(re.compile(PATIENT)).check()
    page.get_by_label("Type de RDV").select_option(label=STAFF_TYPE)
    page.get_by_role("button", name="Continuer").click()
    page.get_by_label("Praticien du département").select_option(label=PROVIDER)
    page.get_by_role("button", name="Continuer").click()
    # Five weeks ahead keeps the slot away from the other journeys' days.
    monday = date.today() + timedelta(days=7 - date.today().weekday() + 35)
    page.goto(f"{page.url}&week={monday.isoformat()}")
    check_accessible(page)
    page.get_by_role("button", name=re.compile("^Réserver à")).first.click()
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est réservé pour le patient.")
    expect(page.locator("dl.facts")).to_contain_text("Personnel")
    check_accessible(page)
    return page.url.split("?")[0]


def test_l_admin_suit_l_activite_exporte_reserve_pour_un_patient_et_lance_les_rappels(
    page: Page, base_url: str
) -> None:
    """Epic E7 : l'admin suit les indicateurs, filtre, exporte, réserve, annule et audite."""
    sign_in(page, base_url, ADMIN)
    page.get_by_role("navigation").get_by_role("link", name="Tableau de bord").first.click()
    expect(page.get_by_role("heading", name="Tableau de bord", level=1)).to_be_visible()
    expect(page.locator("dl.tiles")).to_contain_text("Taux d'absence")
    check_accessible(page)

    page.goto(f"{base_url}/console/appointments/")
    page.get_by_label("Statut").select_option(label="Absent")
    page.get_by_role("button", name="Filtrer").click()
    expect(page).to_have_url(re.compile(r"status=NO_SHOW"))
    rows = page.get_by_role("region", name="Rendez-vous de tous les hôpitaux").locator("tbody tr")
    expect(rows.first).to_contain_text("Absent")
    check_accessible(page)
    with page.expect_download() as download:
        page.get_by_role("button", name="Exporter en CSV").click()
    csv = download.value.path().read_text(encoding="utf-8")
    assert csv.startswith("appointment_id,start,end,status,source"), csv[:80]
    assert ",NO_SHOW," in csv, csv[:400]
    assert ",COMPLETED," not in csv, csv[:400]

    booked = _book_for_patient(page, base_url)
    page.get_by_role("button", name="Annuler le rendez-vous").click()
    check_accessible(page)
    page.get_by_label("Motif de l'annulation").fill(CANCEL_REASON)
    page.get_by_role("button", name="Confirmer l'annulation").click()
    expect(page).to_have_url(re.compile(re.escape(booked)))
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est annulé.")

    page.goto(f"{base_url}/console/audit/")
    page.get_by_label("Acteur (email)").fill(ADMIN)
    page.get_by_label("Entité").select_option("appointment")
    page.get_by_role("button", name="Filtrer").click()
    journal = page.get_by_role("region", name="Entrées du journal d'audit")
    expect(journal).to_contain_text("booking.appointments_exported")
    expect(journal).to_contain_text("booking.appointment_cancelled")
    assert CANCEL_REASON not in journal.inner_text()
    check_accessible(page)

    page.goto(f"{base_url}/console/settings/")
    expect(page.get_by_role("heading", name="Réglages", level=1)).to_be_visible()
    check_accessible(page)
    page.get_by_role("button", name="Lancer les rappels").click()
    expect(page.get_by_role("status")).to_have_text(re.compile(r"^\d+ rappels? envoyés?$"))
    check_accessible(page)
