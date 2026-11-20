from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.test import Client

from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.repositories import DjangoAppointmentTypes
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_session, stored_user
from tests.builders_scheduling import next_monday, stored_department, stored_profile

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def slots_url(kind: Id | str, start: datetime, end: datetime) -> str:
    query = {"type": str(kind), "start": start.isoformat(), "end": end.isoformat()}
    return f"/api/v1/slots?{urlencode(query)}"


def test_without_a_session_slots_answer_unauthenticated(client: Client) -> None:
    """§14 : GET /slots est réservé aux personnes connectées."""
    start = datetime(2026, 12, 1, tzinfo=UTC)

    response = client.get(slots_url(Id(), start, start + timedelta(days=1)))

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_a_range_over_31_days_is_refused_as_invalid(admin_client: Client) -> None:
    """§5.1 : une requête de créneaux couvre 31 jours au plus."""
    start = datetime(2026, 12, 1, tzinfo=UTC)

    response = admin_client.get(slots_url(Id(), start, start + timedelta(days=32)))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"


def test_an_unknown_query_parameter_is_refused_as_invalid(admin_client: Client) -> None:
    start = datetime(2026, 12, 1, tzinfo=UTC)

    response = admin_client.get(f"{slots_url(Id(), start, start + timedelta(days=1))}&page=2")

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"


def test_a_created_rule_then_a_recorded_time_off_change_the_next_answer(client: Client) -> None:
    """Story créneaux libres : plages et absences du praticien donnent ses créneaux libres."""
    department = stored_department()
    clinician = stored_user(Role.CLINICIAN)
    profile = stored_profile(department, user_id=clinician.id)
    kind = build.appointment_type(department.id)
    DjangoAppointmentTypes().save(kind)
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(clinician)
    monday = next_monday()
    url = slots_url(kind.id, monday, monday + timedelta(days=1)) + f"&clinician={profile.id}"
    assert client.get(url).json() == {"slots": []}

    client.post(
        "/workspace/availability/new",
        {"weekday": "1", "start": "09:00", "end": "10:00", "step_minutes": "30"},
    )
    with_rule = client.get(url).json()["slots"]
    client.post(
        "/workspace/time-off/new",
        {"start": f"{monday:%Y-%m-%d}T09:30", "end": f"{monday:%Y-%m-%d}T10:00"},
    )
    with_time_off = client.get(url).json()["slots"]

    nine = monday.replace(hour=9).astimezone(UTC)
    expected = [
        {
            "start": (nine + timedelta(minutes=m)).isoformat(),
            "end": (nine + timedelta(minutes=m + 30)).isoformat(),
        }
        for m in (0, 30)
    ]
    assert with_rule == expected
    assert with_time_off == expected[:1]
    assert with_rule[0]["start"].endswith("+00:00")
