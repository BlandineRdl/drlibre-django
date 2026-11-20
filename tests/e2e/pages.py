from pathlib import Path

from playwright.sync_api import Page

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
