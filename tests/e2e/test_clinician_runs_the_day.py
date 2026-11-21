from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e.pages import (
    check_accessible,
    clear_mail,
    read_link,
    read_mail,
    sign_in,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

PARIS = ZoneInfo("Europe/Paris")
CLINICIAN = "clinicien@drlibre.localhost"
OTHER_CLINICIAN = "clinicien2@drlibre.localhost"
PATIENT = "visiteur@drlibre.localhost"
PATIENT_NAME = "Victor Visiteur"
NOTES = "Tension 12/8, revoir dans un mois"
CANCEL_REASON = "Bloc opératoire imprévu"


def _id_in_link(page: Page, name: str) -> str:
    href = page.get_by_role("link", name=name).first.get_attribute("href") or ""
    return href.strip("/").split("/")[-2]


def _api(page: Page, base_url: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """A POST to the API with the page's own session cookie."""
    return page.request.post(f"{base_url}/api/v1{path}", data=body or {})


def _free_starts(page: Page, base_url: str, *, kind: str, clinician: str, day: date) -> list[str]:
    start = datetime.combine(day, time(), tzinfo=PARIS).astimezone(UTC)
    response = page.request.get(
        f"{base_url}/api/v1/slots",
        params={
            "type": kind,
            "clinician": clinician,
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": (start + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        },
    )
    assert response.ok, response.text()
    return [s["start"] for s in response.json()["slots"]]


def _free_day(page: Page, base_url: str, *, kind: str, clinician: str) -> date:
    """The first weekday from three weeks ahead with room for three appointments."""
    # Three weeks ahead keeps clear of the seeded day and of the patient journeys' weeks.
    # Each run leaves a COMPLETED appointment, so a later run moves on once a day fills up.
    day = date.today() + timedelta(days=21 - date.today().weekday())
    while len(_free_starts(page, base_url, kind=kind, clinician=clinician, day=day)) < 6:
        day += timedelta(days=3 if day.weekday() == 4 else 1)
    return day


def _book(
    page: Page,
    base_url: str,
    *,
    kind: str,
    clinician: str,
    patient: str,
    day: date,
    last: bool = False,
) -> str:
    """Books the patient on the first, or last, free slot of the day through the clinician API."""
    starts = _free_starts(page, base_url, kind=kind, clinician=clinician, day=day)
    start = starts[-1 if last else 0]
    booked = _api(
        page, base_url, "/appointments", {"type": kind, "start": start, "patient": patient}
    )
    assert booked.status == 201, booked.text()
    return booked.json()["id"]


def _patient_id(page: Page, base_url: str) -> str:
    """The passwordless patient, from the seeded appointments of the clinician's agenda."""
    rows = page.request.get(f"{base_url}/api/v1/appointments").json()["appointments"]
    return next(r["patient"] for r in rows if r["patient_name"] == PATIENT_NAME)


def _row(page: Page, appointment_id: str) -> Any:
    link = page.locator(f'a[href="/workspace/appointments/{appointment_id}"]')
    return page.locator("article.agenda-row", has=link)


def _row_action(page: Page, label: str, row: str) -> None:
    page.get_by_role("button", name=f"{label} : {row}").click()


def test_le_praticien_fait_avancer_annule_et_note_ses_rdv_sans_voir_ceux_d_un_autre(
    browser: Browser, base_url: str
) -> None:
    """Epic E6 : arrivé puis terminé, absent, annulé et notifié ; notes privées ; RDV d'un autre."""
    clear_mail(PATIENT)
    admin = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    sign_in(admin, base_url, "admin@drlibre.localhost")
    admin.goto(f"{base_url}/console/appointment-types/?search=HNORD-CONSULT")
    kind = _id_in_link(admin, "Modifier Consultation de cardiologie")
    admin.goto(f"{base_url}/console/clinicians/?search=Martin")
    clinician = _id_in_link(admin, "Calendrier de Claire Martin")
    admin.goto(f"{base_url}/console/clinicians/?search=Bernard")
    other_clinician = _id_in_link(admin, "Calendrier de Hugo Bernard")
    admin.context.close()

    page = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    sign_in(page, base_url, CLINICIAN)
    expect(page).to_have_url(f"{base_url}/workspace/")
    check_accessible(page)
    patient = _patient_id(page, base_url)
    day = _free_day(page, base_url, kind=kind, clinician=clinician)
    ids = [
        _book(page, base_url, kind=kind, clinician=clinician, patient=patient, day=day)
        for _ in range(3)
    ]

    other = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    sign_in(other, base_url, OTHER_CLINICIAN)
    # Booked before the cancel, so « RDV annulé » stays the patient's newest notification.
    # The last slot keeps clear of the patient's morning appointments with the demo clinician.
    _book(
        other, base_url, kind=kind, clinician=other_clinician, patient=patient, day=day, last=True
    )

    page.goto(f"{base_url}/workspace/?day={day}")
    check_accessible(page)
    labels = []
    for appointment_id in ids:
        link = page.locator(f'a[href="/workspace/appointments/{appointment_id}"]')
        labels.append((link.get_attribute("aria-label") or "").removeprefix("Ouvrir : "))
    arrived, absent, cancelled = labels

    _row_action(page, "Arrivé", arrived)
    expect(page.get_by_role("status")).to_have_text("Le patient est noté arrivé.")
    _row_action(page, "Terminé", arrived)
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est terminé.")
    _row_action(page, "Absent", absent)
    expect(page.get_by_role("status")).to_have_text("Le patient est noté absent.")
    expect(_row(page, ids[0])).to_contain_text("Statut : Terminé")
    expect(_row(page, ids[1])).to_contain_text("Statut : Absent")
    check_accessible(page)

    page.get_by_role("link", name=f"Annuler : {cancelled}").click()
    check_accessible(page)
    page.get_by_label("Motif de l'annulation").fill(CANCEL_REASON)
    page.get_by_role("button", name="Confirmer l'annulation").click()
    expect(page.get_by_role("status")).to_have_text("Le rendez-vous est annulé.")
    page.goto(f"{base_url}/workspace/?day={day}")
    expect(_row(page, ids[2])).to_contain_text("Statut : Annulé")
    expect(_row(page, ids[2]).get_by_role("button")).to_have_count(0)

    refused = _api(page, base_url, f"/appointments/{ids[1]}/check-in")
    assert refused.status == 409, refused.text()
    assert refused.json()["code"] == "invalid_transition"
    assert refused.json()["details"] == {"status": "NO_SHOW"}

    page.goto(f"{base_url}/workspace/appointments/{ids[0]}")
    page.get_by_role("textbox", name="Notes cliniques").fill(f"  {NOTES}  ")
    page.get_by_role("button", name="Enregistrer les notes").click()
    expect(page.get_by_role("status")).to_have_text("Les notes cliniques sont enregistrées.")
    expect(page.get_by_role("textbox", name="Notes cliniques")).to_have_value(NOTES)
    history = page.get_by_role("table", name="Historique du rendez-vous")
    expect(history.get_by_role("cell", name="Notes cliniques enregistrées")).to_be_visible()
    expect(history).not_to_contain_text(NOTES)
    check_accessible(page)

    for path in (f"calendar?week={day}", "patients", f"rooms?day={day}"):
        page.goto(f"{base_url}/workspace/{path}")
        check_accessible(page)
    # The other clinician's appointment shows in the shared rooms without its patient.
    expect(page.locator("tbody td.busy").filter(has_text="Occupied").first).to_be_visible()

    response = other.goto(f"{base_url}/workspace/appointments/{ids[0]}")
    assert response is not None
    assert response.status == 403
    expect(other.get_by_text("Not your appointment")).to_be_visible()
    expect(other.locator("main")).not_to_contain_text(PATIENT_NAME)
    check_accessible(other)

    body = read_mail(PATIENT, "Votre rendez-vous est annulé")
    assert CANCEL_REASON not in body, body
    portal = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    portal.goto(f"{base_url}/sign-in")
    portal.locator("#field-link_email").fill(PATIENT)
    portal.get_by_role("button", name="Recevoir un lien").click()
    expect(portal.get_by_role("heading", name="Vérifiez vos emails")).to_be_visible()
    portal.goto(read_link(PATIENT))
    portal.get_by_role("button", name="Continuer").click()
    expect(portal).to_have_url(f"{base_url}/portal/")
    portal.goto(f"{base_url}/portal/notifications")
    expect(portal.locator("article.notification").first.get_by_role("heading")).to_contain_text(
        "RDV annulé"
    )
    portal.goto(f"{base_url}/portal/appointments")
    expect(portal.locator("main")).not_to_contain_text(NOTES)
