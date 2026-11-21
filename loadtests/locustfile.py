"""Search and booking load on the load seed; run through the command in testing.md."""

import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Any, ClassVar

from locust import HttpUser, between, task

MAILPIT = os.environ.get("MAILPIT_URL", "http://localhost:8025")
API = "/api/v1"
FILTERS = (
    {"moment": "morning"},
    {"moment": "afternoon", "window": "7"},
    {"sort": "name"},
    {"q": "Charge"},
)


def mailpit_code(email: str, wait: float = 10) -> str | None:
    """The 6-digit code of the verification email sent to this address."""
    query = urllib.parse.urlencode({"query": f"to:{email}"})
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{MAILPIT}/api/v1/search?{query}", timeout=5) as found:  # noqa: S310  # nosec B310
            messages = json.load(found)["messages"]
        if messages:
            with urllib.request.urlopen(  # noqa: S310  # nosec B310
                f"{MAILPIT}/api/v1/message/{messages[0]['ID']}", timeout=5
            ) as message:
                match = re.search(r"\b(\d{6})\b", json.load(message)["Text"])
            return match.group(1) if match else None
        time.sleep(0.2)
    return None


def _failure_code(response: Any) -> str:
    """The error code of the standard body, else the bare HTTP status."""
    try:
        return str(response.json()["code"])
    except (ValueError, KeyError, TypeError):
        return f"http_{response.status_code}"


def _count(response: Any, name: str, *, ok: bool) -> bool:
    """Count a real success under its endpoint; a refusal apart, by error code, never as success."""
    if ok:
        response.success()
    else:
        response.request_meta["name"] = f"{name} refused"
        response.failure(_failure_code(response))
    return ok


class Visitor(HttpUser):
    """Searches, books anonymously with a code from Mailpit, then books signed in."""

    wait_time = between(0.5, 2)
    providers: ClassVar[list[dict[str, Any]]] = []
    specialties: ClassVar[list[str]] = []

    def on_start(self) -> None:
        if not Visitor.providers:
            Visitor.providers = [
                p
                for page in (1, 2, 3)
                for p in self.client.get(
                    f"{API}/search/providers?page={page}", name="setup"
                ).json()["items"]
                if p["next_slots"]
            ]
            Visitor.specialties = [
                s["id"]
                for s in self.client.get(f"{API}/search/specialties", name="setup").json()["items"]
            ]

    def _slot(self) -> tuple[dict[str, Any], str] | None:
        """A random free start of a random provider over the next 30 days, read fresh."""
        if not Visitor.providers:
            return None
        provider = random.choice(Visitor.providers)  # noqa: S311
        first = provider["next_slots"]["starts"][0]
        end = (datetime.fromisoformat(first) + timedelta(days=30)).isoformat()
        found = self.client.get(
            f"{API}/slots",
            params={
                "type": provider["next_slots"]["type_id"],
                "clinician": provider["id"],
                "start": first,
                "end": end,
            },
            name="free slots",
        ).json()["slots"]
        return (provider, random.choice(found)["start"]) if found else None  # noqa: S311

    @task(6)
    def search_providers(self) -> None:
        params = {**random.choice(FILTERS)}  # noqa: S311
        if Visitor.specialties and random.random() < 0.5:  # noqa: S311
            params["specialty"] = random.choice(Visitor.specialties)  # noqa: S311
        self.client.get(f"{API}/search/providers", params=params, name="search providers")

    @task(3)
    def search_hospitals(self) -> None:
        self.client.get(f"{API}/search/hospitals", name="search hospitals")

    @task(3)
    def search_specialties(self) -> None:
        self.client.get(f"{API}/search/specialties", name="search specialties")

    @task(2)
    def search_page(self) -> None:
        self.client.get("/?moment=morning", name="search page")

    @task(3)
    def provider_page(self) -> None:
        if picked := self._slot():
            self.client.get(f"{API}/providers/{picked[0]['id']}", name="provider page")

    @task(2)
    def free_slots(self) -> None:
        self._slot()

    @task(1)
    def book(self) -> None:
        if not (picked := self._slot()):
            return
        provider, start = picked
        email = f"load-visitor-{uuid.uuid4().hex[:12]}@example.org"
        with self.client.post(
            f"{API}/booking/holds",
            json={
                "type": provider["next_slots"]["type_id"],
                "clinician": provider["id"],
                "start": start,
                "full_name": "Visiteur Charge",
                "birth_date": "1990-01-01",
                "email": email,
                "accepted_terms": True,
            },
            name="booking hold",
            catch_response=True,
        ) as held:
            created = _count(held, "booking hold", ok=held.status_code == 201)
        code = mailpit_code(email) if created else None
        if code is None:
            return
        with self.client.post(
            f"{API}/booking/holds/{held.json()['hold_id']}/verify",
            json={"code": code},
            name="booking verify",
            catch_response=True,
        ) as verified:
            booked = verified.status_code == 200 and "appointment" in verified.text
            if not _count(verified, "booking verify", ok=booked):
                self.client.cookies.clear()
                return
        # The verified visitor now holds a session cookie: <redacted>
        if picked := self._slot():
            provider, start = picked
            with self.client.post(
                f"{API}/appointments",
                json={
                    "type": provider["next_slots"]["type_id"],
                    "clinician": provider["id"],
                    "start": start,
                },
                name="signed-in booking",
                catch_response=True,
            ) as signed:
                _count(signed, "signed-in booking", ok=signed.status_code == 201)
        self.client.cookies.clear()
