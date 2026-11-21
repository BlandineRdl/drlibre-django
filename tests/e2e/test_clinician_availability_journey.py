from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e.pages import check_accessible, save, sign_in

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

PARIS = ZoneInfo("Europe/Paris")


def _id_in_link(page: Page, name: str) -> str:
    href = page.get_by_role("link", name=name).first.get_attribute("href") or ""
    return href.strip("/").split("/")[-2]


def _slots(page: Page, base_url: str, *, kind: str, clinician: str, day: date) -> list[str]:
    """Local start times of the day's free slots, read with the page's own session."""
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
    return [
        f"{datetime.fromisoformat(s['start']).astimezone(PARIS):%H:%M}"
        for s in response.json()["slots"]
    ]


def _delete_all(page: Page, url: str, link_name: str) -> None:
    """Removes what an earlier interrupted run left, so the journey can run again."""
    page.goto(url)
    links = page.get_by_role("link", name=link_name)
    while links.count():
        links.first.click()
        page.get_by_role("button", name="Supprimer").click()
        expect(page.get_by_role("status")).to_be_visible()


def test_demo_clinician_publishes_a_rule_and_a_time_off_and_free_slots_follow(
    browser: Browser, base_url: str
) -> None:
    """Epic E2 : le praticien de démo crée une plage puis une absence ; les créneaux suivent."""
    saturday = date.today() + timedelta(days=(5 - date.today().weekday()) % 7 + 7)
    admin = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    sign_in(admin, base_url, "admin@drlibre.localhost")
    admin.goto(f"{base_url}/console/appointment-types/?search=HNORD-CONSULT")
    kind = _id_in_link(admin, "Modifier Consultation de cardiologie")
    admin.goto(f"{base_url}/console/clinicians/?search=Martin")
    clinician = _id_in_link(admin, "Calendrier de Claire Martin")

    page = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    sign_in(page, base_url, "clinicien@drlibre.localhost")
    _delete_all(page, f"{base_url}/workspace/time-off/", "Supprimer l'absence")
    _delete_all(page, f"{base_url}/workspace/availability/", "Supprimer la plage Samedi")
    assert _slots(page, base_url, kind=kind, clinician=clinician, day=saturday) == []

    page.goto(f"{base_url}/workspace/availability/new")
    check_accessible(page)
    page.get_by_label("Jour").select_option(label="Samedi")
    page.get_by_label("Début").fill("08:00")
    page.get_by_label("Fin").fill("10:00")
    page.get_by_label("Pas en minutes").fill("30")
    save(page)
    expect(page.get_by_role("status")).to_be_visible()
    expect(page.get_by_role("rowheader", name="Samedi")).to_be_visible()
    check_accessible(page)
    assert _slots(page, base_url, kind=kind, clinician=clinician, day=saturday) == [
        "08:00",
        "08:30",
        "09:00",
        "09:30",
    ]

    page.goto(f"{base_url}/workspace/time-off/new")
    page.get_by_label("Début").fill(f"{saturday}T08:00")
    page.get_by_label("Fin").fill(f"{saturday}T09:00")
    page.get_by_label("Motif").fill("Formation")
    save(page)
    expect(page.get_by_role("status")).to_be_visible()
    expect(page.get_by_role("cell", name="Formation")).to_be_visible()
    check_accessible(page)
    assert _slots(page, base_url, kind=kind, clinician=clinician, day=saturday) == [
        "09:00",
        "09:30",
    ]

    admin.goto(f"{base_url}/console/clinicians/?search=Martin")
    expect(admin.get_by_role("cell", name="Sam 08:00-10:00")).to_be_visible()
    admin.get_by_role("link", name="Calendrier de Claire Martin").click()
    admin.goto(f"{admin.url}?week={saturday}")
    grid = admin.get_by_role("region", name=f"Semaine du {saturday - timedelta(days=5):%d/%m/%Y}")
    expect(grid.get_by_role("cell", name="Absence")).to_have_count(2)
    expect(grid.get_by_role("cell", name="Disponible").first).to_be_visible()
    check_accessible(admin)

    _delete_all(page, f"{base_url}/workspace/time-off/", "Supprimer l'absence")
    _delete_all(page, f"{base_url}/workspace/availability/", "Supprimer la plage Samedi")
