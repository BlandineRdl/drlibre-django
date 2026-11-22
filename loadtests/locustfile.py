"""Visitor, patient, clinician and admin load on the load seed; run by `scripts/load-run.sh`."""

import json
import os
import random
import re
import time
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta
from itertools import count
from typing import Any, ClassVar

from locust import HttpUser, between, task
from locust.exception import StopUser

MAILPIT = os.environ.get("MAILPIT_URL", "http://localhost:8025")
API = "/api/v1"
# Set by load-run.sh from scripts.seed.DEMO_PASSWORD, so the literal stays in the seed.
PASSWORD = os.environ.get("LOAD_PASSWORD", "")
LOAD_PATIENTS = 5000
LOAD_CLINICIANS = 200
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
FILTERS = (
    {"moment": "morning"},
    {"moment": "afternoon", "window": "7"},
    {"sort": "name"},
    {"q": "Charge"},
)


def mailpit_code(email: str) -> str | None:
    """The 6-digit code of the verification email sent to this address."""
    return mailpit_match(email, r"\b(\d{6})\b")


def mailpit_match(email: str, pattern: str, wait: float = 10) -> str | None:
    """The first group of `pattern` in the latest email sent to this address."""
    query = urllib.parse.urlencode({"query": f"to:{email}"})
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{MAILPIT}/api/v1/search?{query}", timeout=5) as found:  # noqa: S310  # nosec B310
            messages = json.load(found)["messages"]
        if messages:
            with urllib.request.urlopen(  # noqa: S310  # nosec B310
                f"{MAILPIT}/api/v1/message/{messages[0]['ID']}", timeout=5
            ) as message:
                match = re.search(pattern, json.load(message)["Text"])
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

    weight = 8
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
        provider = random.choice(Visitor.providers)  # noqa: S311  # nosec B311
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
        return (provider, random.choice(found)["start"]) if found else None  # noqa: S311  # nosec B311

    @task(6)
    def search_providers(self) -> None:
        params = {**random.choice(FILTERS)}  # noqa: S311  # nosec B311
        if Visitor.specialties and random.random() < 0.5:  # noqa: S311  # nosec B311
            params["specialty"] = random.choice(Visitor.specialties)  # noqa: S311  # nosec B311
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

    @task(2)
    def fhir_slot_search(self) -> None:
        """A FHIR client's free Slot search of a type over a week, without a token."""
        if not Visitor.providers:
            return
        slots = random.choice(Visitor.providers)["next_slots"]  # noqa: S311  # nosec B311
        first = datetime.fromisoformat(slots["starts"][0])
        params = [
            ("service-type", slots["type_id"]),
            ("start", f"ge{first.isoformat()}"),
            ("start", f"lt{(first + timedelta(days=7)).isoformat()}"),
        ]
        self.client.get("/fhir/Slot", params=params, name="fhir slot search")

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


class SignedIn(HttpUser):
    """A signed-in role: a GET succeeds on 200 only, a redirect to sign-in is a refusal."""

    abstract = True
    weight = 4
    wait_time = between(0.5, 1.5)

    def _get(self, path: str, name: str, params: dict[str, Any] | None = None) -> Any:
        with self.client.get(
            path, params=params, name=name, allow_redirects=False, catch_response=True
        ) as response:
            _count(response, name, ok=response.status_code == 200)
        return response

    def _password_sign_in(self, email: str) -> None:
        with self.client.post(
            f"{API}/auth/login",
            json={"email": email, "password": PASSWORD},
            name="sign-in",
            catch_response=True,
        ) as signed:
            ok = _count(signed, "sign-in", ok=signed.status_code == 200)
        if not ok:
            # A wrong password repeated would lock the account: stop the whole run.
            if self.environment.runner:
                self.environment.runner.quit()
            raise StopUser


class Patient(SignedIn):
    """Signs in by emailed link, then reads the portal (E4) and the patient API list."""

    numbers = count(random.randrange(LOAD_PATIENTS))  # noqa: S311  # nosec B311

    def on_start(self) -> None:
        # Distinct patients per user keep each email under its hourly link limit.
        email = f"load-patient-{next(Patient.numbers) % LOAD_PATIENTS:05}@drlibre.localhost"
        with self.client.post(
            f"{API}/auth/link", json={"email": email}, name="sign-in", catch_response=True
        ) as sent:
            token = mailpit_match(email, r"token=([^\s&]+)") if sent.status_code == 202 else None
            _count(sent, "sign-in", ok=token is not None)
        if token is None:
            raise StopUser
        with self.client.post(
            f"{API}/auth/link/verify",
            json={"token": urllib.parse.unquote(token)},
            name="sign-in",
            catch_response=True,
        ) as verified:
            ok = _count(verified, "sign-in", ok=verified.status_code == 200)
        if not ok:
            raise StopUser

    @task
    def portal_home(self) -> None:
        self._get("/portal/", "portal home")

    @task
    def portal_appointments(self) -> None:
        self._get("/portal/appointments", "portal appointments")

    @task
    def portal_notifications(self) -> None:
        self._get("/portal/notifications", "portal notifications")

    @task
    def api_list(self) -> None:
        self._get(f"{API}/appointments", "api appointments patient")


class Clinician(SignedIn):
    """Signs in by password, then reads the workspace (E6) and the clinician API list."""

    def on_start(self) -> None:
        number = random.randrange(LOAD_CLINICIANS)  # noqa: S311  # nosec B311
        self._password_sign_in(f"load-clinician-{number:03}@drlibre.localhost")
        listed = self.client.get(f"{API}/appointments", name="setup").json()
        self.appointments = [a["id"] for a in listed.get("appointments", [])]

    @task
    def today(self) -> None:
        self._get("/workspace/", "workspace today")

    @task
    def calendar(self) -> None:
        self._get("/workspace/calendar", "workspace calendar")

    @task
    def appointment_file(self) -> None:
        if self.appointments:
            picked = random.choice(self.appointments)  # noqa: S311  # nosec B311
            self._get(f"/workspace/appointments/{picked}", "workspace appointment file")

    @task
    def api_list(self) -> None:
        self._get(f"{API}/appointments", "api appointments clinician")


class Admin(SignedIn):
    """Signs in as the demo admin, then reads the console (E7) and the admin API list."""

    departments: ClassVar[list[str]] = []

    def on_start(self) -> None:
        self._password_sign_in("admin@drlibre.localhost")
        if not Admin.departments:
            page = self.client.get("/console/appointments/", name="setup").text
            select = page.partition('name="department"')[2].partition("</select>")[0]
            Admin.departments = re.findall(f'value="({UUID})"', select)

    def _filters(self) -> dict[str, str]:
        """A status, a 14-day window around today and a random department, as dates."""
        today = date.today()
        params = {
            "status": random.choice(("BOOKED", "COMPLETED")),  # noqa: S311  # nosec B311
            "from": (today - timedelta(days=7)).isoformat(),
            "to": (today + timedelta(days=7)).isoformat(),
        }
        if Admin.departments:
            params["department"] = random.choice(Admin.departments)  # noqa: S311  # nosec B311
        return params

    @task
    def dashboard_week(self) -> None:
        self._get("/console/", "console dashboard 7d", {"range": "7"})

    @task
    def dashboard_month(self) -> None:
        self._get("/console/", "console dashboard 30d", {"range": "30"})

    @task
    def filtered_list(self) -> None:
        self._get("/console/appointments/", "console appointments filtered", self._filters())

    @task
    def later_page(self) -> None:
        page = str(random.randint(2, 50))  # noqa: S311  # nosec B311
        self._get("/console/appointments/", "console appointments page", {"page": page})

    @task
    def export(self) -> None:
        self._get("/console/appointments/export.csv", "console export", self._filters())

    @task
    def audit(self) -> None:
        page = str(random.randint(1, 50))  # noqa: S311  # nosec B311
        self._get("/console/audit/", "console audit page", {"page": page})

    @task
    def audit_filtered(self) -> None:
        params = {"entity_type": "appointment", "page": "2"}
        self._get("/console/audit/", "console audit filtered", params)

    @task
    def api_list(self) -> None:
        # The API takes aware datetimes, the console bare dates.
        params = self._filters()
        for key in ("from", "to"):
            params[key] = f"{params[key]}T00:00:00+01:00"
        self._get(f"{API}/appointments", "api appointments admin", params)
