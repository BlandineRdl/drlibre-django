import re

import pytest
from django.conf import settings
from django.test import Client

from drlibre.identity.domain.user import Role
from drlibre.organisation.domain.department import Department
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel
from tests.builders import stored_session, stored_user
from tests.builders_scheduling import next_monday, stored_department, stored_profile

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

MONDAY_MORNING = {"weekday": "1", "start": "09:00", "end": "12:00", "step_minutes": "15"}


def clinician_client(department: Department) -> tuple[Client, str]:
    user = stored_user(Role.CLINICIAN)
    profile = stored_profile(department, user_id=user.id)
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(user)
    return client, str(profile.id)


def test_a_clinician_sees_only_own_rules_and_another_ones_answers_403() -> None:
    """Story plages : le praticien ne voit et ne modifie que ses propres plages."""
    department = stored_department()
    mine, _ = clinician_client(department)
    theirs, their_profile = clinician_client(department)
    theirs.post("/workspace/availability/new", MONDAY_MORNING)
    their_rule = AvailabilityRuleModel.objects.get(clinician_id=their_profile)

    listing = mine.get("/workspace/availability/").content.decode()
    edit = mine.get(f"/workspace/availability/{their_rule.id}/edit")
    delete = mine.post(f"/workspace/availability/{their_rule.id}/delete")

    assert "Aucune plage pour l'instant." in listing
    assert "Fuseau : Europe/Paris" in listing
    assert (edit.status_code, delete.status_code) == (403, 403)
    assert AvailabilityRuleModel.objects.filter(id=their_rule.id).exists()


def test_an_overlapping_rule_re_renders_the_form_with_focus_on_the_field() -> None:
    """Story plages : deux plages du même jour ne se chevauchent pas ; le refus le dit."""
    client, _ = clinician_client(stored_department())
    client.post("/workspace/availability/new", MONDAY_MORNING)

    response = client.post(
        "/workspace/availability/new", {**MONDAY_MORNING, "start": "11:00", "end": "13:00"}
    )

    body = response.content.decode()
    assert response.status_code == 400
    assert 'role="alert"' in body
    assert "chevauche la plage Lundi 09:00-12:00" in body
    assert re.search(r'id="field-start"[^>]*aria-invalid="true"[^>]*autofocus', body)


def test_the_admin_week_calendar_offers_no_write_action(admin_client: Client) -> None:
    """Story calendrier : lecture seule, fuseau de l'hôpital nommé."""
    client, profile = clinician_client(stored_department())
    client.post("/workspace/availability/new", MONDAY_MORNING)

    fallback = admin_client.get(f"/console/clinicians/{profile}/week?week=not-a-date")
    response = admin_client.get(f"/console/clinicians/{profile}/week?week={next_monday():%Y-%m-%d}")

    body = response.content.decode()
    assert fallback.status_code == 200
    main = body.split("<main", 1)[1].split("</main>", 1)[0]
    assert response.status_code == 200
    assert "Fuseau : Europe/Paris" in main
    assert ">Disponible</td>" in main
    assert "<form" not in main


def test_the_clinicians_summary_reflects_an_edit_immediately(admin_client: Client) -> None:
    """Story résumé hebdomadaire : le résumé reflète une plage modifiée dès son enregistrement."""
    client, profile = clinician_client(stored_department())
    client.post("/workspace/availability/new", MONDAY_MORNING)
    rule = AvailabilityRuleModel.objects.get(clinician_id=profile)
    before = admin_client.get("/console/clinicians/").content.decode()

    client.post(
        f"/workspace/availability/{rule.id}/edit",
        {**MONDAY_MORNING, "start": "14:00", "end": "17:00"},
    )
    after = admin_client.get("/console/clinicians/").content.decode()

    assert "<td>Lun 09:00-12:00</td>" in before
    assert "<td>Lun 14:00-17:00</td>" in after
    assert f'href="/console/clinicians/{profile}/week"' in after
