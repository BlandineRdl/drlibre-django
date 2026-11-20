import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

AXE = Path(__file__).parent / "vendor" / "axe-4.14.1.min.js"
DEMO_PASSWORD = "drlibre-demo-2026"
WIDTHS = (375, 1440)
WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def check_accessible(page: Page) -> None:
    """No WCAG 2.x A/AA violation and no horizontal scroll, on a phone and on a desktop."""
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 900})
        page.add_script_tag(path=str(AXE))
        violations = page.evaluate(
            "async (tags) => (await axe.run(document, {runOnly: {type: 'tag', values: tags}}))"
            ".violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).join(', '))",
            WCAG,
        )
        assert violations == [], f"{page.url} at {width}px: {violations}"
        scroll = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert scroll <= 0, f"{page.url} scrolls horizontally at {width}px"


def sign_in(page: Page, base_url: str, email: str, password: str = DEMO_PASSWORD) -> None:
    page.goto(f"{base_url}/sign-in")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Mot de passe", exact=True).fill(password)
    page.get_by_role("button", name="Se connecter").click()


def save(page: Page) -> None:
    page.get_by_role("button", name="Enregistrer").click()


def test_anonymous_visitor_is_sent_to_sign_in(page: Page, base_url: str) -> None:
    """Chaque rôle : sans session, toute page non publique renvoie vers la connexion."""
    page.goto(f"{base_url}/console/")

    expect(page).to_have_url(f"{base_url}/sign-in?next=%2Fconsole%2F")
    check_accessible(page)


def test_demo_clinician_sees_forbidden_in_the_console(page: Page, base_url: str) -> None:
    """Chaque rôle : un praticien qui ouvre la console voit une page « forbidden »."""
    sign_in(page, base_url, "clinicien@drlibre.localhost")
    expect(page).to_have_url(f"{base_url}/workspace/")

    page.goto(f"{base_url}/console/")

    expect(page.get_by_role("heading", name="Accès refusé")).to_be_visible()


def test_admin_builds_a_hospital_referential_and_cannot_delete_a_used_hospital(
    browser: Browser, base_url: str
) -> None:
    """Epic E1: hospital, department, room, type, clinician account and profile, refused delete."""
    page = browser.new_context(bypass_csp=True, locale="fr-FR").new_page()
    run = uuid.uuid4().hex[:6].upper()
    sign_in(page, base_url, "admin@drlibre.localhost")
    expect(page).to_have_url(f"{base_url}/console/")

    page.goto(f"{base_url}/console/hospitals/new")
    check_accessible(page)
    page.get_by_label("Nom", exact=True).fill(f"Hôpital E2E {run}")
    page.get_by_label("Code", exact=True).fill(f"E2E-H{run}")
    page.get_by_label("Adresse").fill("1 rue du Test")
    page.get_by_label("Code postal").fill("59000")
    page.get_by_label("Ville").fill("Lille")
    page.get_by_label("Téléphone").fill("+33 3 20 00 00 00")
    save(page)
    expect(page.get_by_role("status")).to_have_text("L'élément a été créé.")
    page.goto(f"{base_url}/console/hospitals/?search=E2E-H{run}")
    expect(page.get_by_role("cell", name=f"E2E-H{run}", exact=True)).to_be_visible()
    check_accessible(page)

    page.goto(f"{base_url}/console/departments/new")
    page.get_by_label("Hôpital").select_option(label=f"Hôpital E2E {run} (E2E-H{run})")
    page.get_by_label("Nom", exact=True).fill(f"Cardiologie {run}")
    page.get_by_label("Code", exact=True).fill(f"E2E-D{run}")
    save(page)
    expect(page.get_by_role("status")).to_be_visible()
    department = f"Cardiologie {run} (E2E-D{run}) · Hôpital E2E {run}"

    page.goto(f"{base_url}/console/rooms/new")
    page.get_by_label("Département").select_option(label=department)
    page.get_by_label("Nom", exact=True).fill(f"Salle {run}")
    page.get_by_label("Code", exact=True).fill(f"E2E-R{run}")
    page.get_by_label("Étage").fill("1")
    save(page)
    expect(page.get_by_role("status")).to_be_visible()

    page.goto(f"{base_url}/console/appointment-types/new")
    page.get_by_label("Département").select_option(label=department)
    page.get_by_label("Nom", exact=True).fill(f"Consultation {run}")
    page.get_by_label("Code", exact=True).fill(f"E2E-T{run}")
    page.get_by_label("Durée en minutes").fill("0")
    save(page)
    expect(page.get_by_label("Durée en minutes")).to_be_focused()
    check_accessible(page)
    page.get_by_label("Durée en minutes").fill("20")
    save(page)
    expect(page.get_by_role("status")).to_be_visible()

    page.goto(f"{base_url}/console/users/new")
    page.get_by_label("Nom complet").fill(f"Dr E2E {run}")
    page.get_by_label("Email").fill(f"E2E.{run}@Example.org")
    page.get_by_label("Rôle").select_option(label="Praticien")
    page.get_by_label("Mot de passe temporaire").fill("temporary-pass-1")
    save(page)
    page.goto(f"{base_url}/console/users/?search=e2e.{run.lower()}@example.org")
    expect(
        page.get_by_role("cell", name=f"e2e.{run.lower()}@example.org", exact=True)
    ).to_be_visible()

    page.goto(f"{base_url}/console/clinicians/new")
    page.get_by_label("Praticien", exact=True).select_option(label=f"Dr E2E {run}")
    page.get_by_label("Département").select_option(label=department)
    page.get_by_label("Spécialité").select_option(label="Cardiologie (CARDIO)")
    page.get_by_label("Titre").fill(f"Dr E2E {run}")
    page.get_by_label("Salle par défaut").select_option(
        label=f"Salle {run} (E2E-R{run}) · Cardiologie {run}"
    )
    save(page)
    page.goto(f"{base_url}/console/clinicians/?search={run}")
    expect(page.get_by_role("cell", name=f"Dr E2E {run}", exact=True).first).to_be_visible()

    page.goto(f"{base_url}/console/hospitals/?search=E2E-H{run}")
    page.get_by_role("link", name=f"Supprimer Hôpital E2E {run} (E2E-H{run})").click()
    expect(
        page.get_by_role("heading", name=f"Supprimer « Hôpital E2E {run} (E2E-H{run}) » ?")
    ).to_be_visible()
    check_accessible(page)
    page.get_by_role("button", name="Supprimer").click()
    expect(page.get_by_role("alert")).to_contain_text(
        f"Département : Cardiologie {run} (E2E-D{run})"
    )
    check_accessible(page)
