import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import redis
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
    page.locator("#field-email").fill(email)
    page.get_by_label("Mot de passe", exact=True).fill(password)
    page.get_by_role("button", name="Se connecter").click()


def save(page: Page) -> None:
    page.get_by_role("button", name="Enregistrer").click()


MAILPIT = os.environ.get("E2E_MAILPIT_URL", "http://localhost:8025")
REDIS_URL = os.environ.get("E2E_REDIS_URL", "redis://localhost:6379/0")


def reset_rate_limits() -> None:
    """Every host client shares one address behind Docker, so flush the compose rate limits."""
    client = redis.Redis.from_url(REDIS_URL)
    for key in client.scan_iter("drlibre:rate:*"):
        client.delete(key)


def _mail_text(to: str, subject: str = "", wait: float = 15) -> str:
    """The body of the newest email sent to this address, waiting for the worker to send it."""
    search = f"to:{to}" + (f' subject:"{subject}"' if subject else "")
    query = urllib.parse.urlencode({"query": search})
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{MAILPIT}/api/v1/search?{query}", timeout=5) as found:  # noqa: S310  # nosec B310
            messages = json.load(found)["messages"]
        if messages:
            with urllib.request.urlopen(  # noqa: S310  # nosec B310
                f"{MAILPIT}/api/v1/message/{messages[0]['ID']}", timeout=5
            ) as message:
                return json.load(message)["Text"]
        time.sleep(0.3)
    raise AssertionError(f"no email for {to} {subject!r} in Mailpit")


def clear_mail(to: str) -> None:
    """Deletes every email sent to this address, so each subject read next is this run's."""
    query = urllib.parse.urlencode({"query": f"to:{to}"})
    url = f"{MAILPIT}/api/v1/search?{query}"
    request = urllib.request.Request(url, method="DELETE")  # noqa: S310  # nosec B310
    urllib.request.urlopen(request, timeout=5).close()  # noqa: S310  # nosec B310


def read_mail(to: str, subject: str) -> str:
    return _mail_text(to, subject)


def read_code(to: str) -> str:
    match = re.search(r"\b(\d{6})\b", _mail_text(to))
    assert match, "no 6-digit code in the email"
    return match.group(1)


def read_link(to: str) -> str:
    body = read_mail(to, "Votre lien de connexion")
    match = re.search(r"https?://\S+/sign-in/link\?token=\S+", body)
    assert match, "no sign-in link in the email"
    return match.group(0)
