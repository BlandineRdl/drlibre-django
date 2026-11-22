"""Epic E8 Success Evidence on the demo seed and its fixed bearer tokens."""

import json
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.test import Client

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.registry import declared
from drlibre.interfaces.fhir.slot_id import SlotKey, slot_id, slot_key
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from drlibre.shared_kernel.ids import Id
from scripts import seed
from tests.builders import stored_session

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PATIENT_TOKEN = "demo-patient-token"  # nosec B105
PATIENT_EMAIL = "patient@drlibre.localhost"
REASON = "Empêchement"
FEATURES = Path(__file__).resolve().parent.parent / "features" / "fhir"

# Each declared write and the scenario showing it refused as the screen or the API refuses it.
SAME_REFUSAL: dict[tuple[str, str], tuple[str, str]] = {
    ("POST", "Appointment"): (
        "un_client_reserve_et_consulte_des_rdv_en_fhir",
        "Les refus sont ceux des écrans dans les mêmes cas",
    ),
    ("PUT", "Appointment"): (
        "un_client_deplace_annule_et_change_le_statut_d_un_rdv_en_fhir",
        "(comme par l'API)",
    ),
    ("POST", "AppointmentResponse"): (
        "un_patient_rejoint_la_liste_d_attente_et_accepte_une_offre_en_fhir",
        "(créneau déjà pris)",
    ),
    ("PUT", "Communication"): (
        "un_client_lit_les_notifications_de_son_utilisateur_en_fhir",
        "| déjà lue ",
    ),
    ("POST", "Schedule"): (
        "le_praticien_gere_ses_disponibilites_en_fhir",
        "| créer une plage au nom d'un autre ",
    ),
    ("PUT", "Schedule"): (
        "le_praticien_gere_ses_disponibilites_en_fhir",
        "| modifier la plage d'un autre ",
    ),
    ("DELETE", "Schedule"): (
        "le_praticien_gere_ses_disponibilites_en_fhir",
        "| supprimer la plage d'un autre ",
    ),
    **{
        (method, kind): ("l_admin_gere_le_referentiel_en_fhir", f"| {case} ")
        for method, kind, case in (
            ("POST", "Organization", "un praticien crée un hôpital"),
            ("PUT", "Organization", "un praticien modifie un hôpital"),
            ("DELETE", "Organization", "un patient supprime un département"),
            ("POST", "Location", "un praticien crée une salle"),
            ("PUT", "Location", "un patient modifie une salle"),
            ("DELETE", "Location", "un patient supprime une salle"),
            ("POST", "HealthcareService", "un patient crée un type de RDV"),
            ("PUT", "HealthcareService", "un praticien modifie un type de RDV"),
            ("DELETE", "HealthcareService", "un praticien supprime un type de RDV"),
            ("POST", "CodeSystem", "un patient crée une spécialité"),
            ("PUT", "CodeSystem", "un praticien modifie une spécialité"),
            ("DELETE", "CodeSystem", "un patient supprime une spécialité"),
            ("POST", "ValueSet", "un patient crée un jeu de valeurs"),
            ("PUT", "ValueSet", "un praticien modifie un jeu de valeurs"),
            ("DELETE", "ValueSet", "un patient supprime un jeu de valeurs"),
            ("POST", "Practitioner", "un patient crée un praticien"),
            ("PUT", "Practitioner", "un praticien modifie un praticien"),
            ("DELETE", "Practitioner", "un praticien supprime un praticien"),
            ("POST", "PractitionerRole", "un praticien crée un profil"),
            ("PUT", "PractitionerRole", "un patient modifie un profil"),
            ("DELETE", "PractitionerRole", "un patient supprime un profil"),
            ("POST", "Patient", "un praticien ne crée pas de patient"),
            ("PUT", "Patient", "un praticien ne modifie pas un patient"),
            ("DELETE", "Patient", "un patient ne supprime pas sa fiche"),
        )
    },
}


@pytest.fixture
def demo() -> None:
    seed.main()


def _fhir(method: str, path: str, body: Any = None, **headers: str) -> Any:
    sent = {"Authorization": f"Bearer {headers.pop('token')}"} if "token" in headers else {}
    data = json.dumps(body) if body is not None else ""
    return Client().generic(method, path, data, "application/fhir+json", headers=sent | headers)


def _user(email: str) -> Id:
    return Id(UserRecord.objects.get(email=email).id)


def _free_slots(kind: str) -> list[dict[str, Any]]:
    """A visitor's search of the type's free slots over a week, from three days ahead."""
    first = datetime.combine(
        datetime.now(ZoneInfo(settings.TIME_ZONE)).date() + timedelta(days=3), time()
    ).replace(tzinfo=ZoneInfo(settings.TIME_ZONE))
    query = (
        ("service-type", kind),
        ("start", f"ge{first.isoformat()}"),
        ("start", f"lt{(first + timedelta(days=7)).isoformat()}"),
        ("_count", "100"),
    )
    response = _fhir("GET", f"/fhir/Slot?{urlencode(query)}")
    assert response.status_code == 200, response.json()
    return [e["resource"] for e in response.json().get("entry", [])]


def _two_days_apart(slots: list[dict[str, Any]]) -> tuple[SlotKey, SlotKey]:
    """Two free slots of one clinician on different days, so one patient may book both."""
    keys = [k for k in (slot_key(s["id"]) for s in slots) if k is not None]
    first = keys[0]
    second = next(
        k
        for k in keys
        if k.clinician_id == first.clinician_id and k.start.date() != first.start.date()
    )
    return first, second


def _references(body: dict[str, Any]) -> list[str]:
    return [p["actor"]["reference"] for p in body.get("participant", [])]


def _trace(appointment: Id) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit = AuditEntryRecord.objects.filter(entity_id=appointment.value).order_by("at")
    notices = NotificationRecord.objects.filter(appointment_id=appointment.value)
    return (
        list(audit.values("action", "entity_type", "metadata", "actor_id")),
        list(notices.order_by("created_at").values("recipient_id", "kind", "title")),
    )


def test_a_free_slot_found_without_a_token_is_booked_then_cancelled_like_on_the_screens(
    demo: None,
) -> None:
    """Epic E8 Success Evidence: booked with practitioner and room, cancelled, same trace."""
    kind = str(AppointmentTypeRecord.objects.get(code="HNORD-CONSULT").id)
    in_fhir, on_screen = _two_days_apart(_free_slots(kind))
    coding = {"system": f"{base_url()}/HealthcareService", "code": kind}
    booked = _fhir(
        "POST",
        "/fhir/Appointment",
        {
            "resourceType": "Appointment",
            "status": "proposed",
            "serviceType": [{"coding": [coding]}],
            "slot": [{"reference": f"Slot/{slot_id(in_fhir)}"}],
        },
        token=PATIENT_TOKEN,
    )
    body = booked.json()
    assert booked.status_code == 201, body
    assert body["status"] == "booked"
    references = _references(body)
    assert f"Patient/{_user(PATIENT_EMAIL)}" in references
    assert any(r.startswith("Practitioner/") for r in references)
    assert any(r.startswith("Location/") for r in references)
    fhir_id = Id.parse(body["id"])

    patient = DjangoUsers().get(_user(PATIENT_EMAIL))
    assert patient is not None
    screen = Client()
    screen.cookies[settings.SESSION_COOKIE_NAME] = stored_session(patient)
    form = {
        "type": kind,
        "clinician": str(on_screen.clinician_id),
        "start": on_screen.start.isoformat(),
    }
    placed = screen.post("/booking/new", form)
    assert placed.status_code == 302, placed.content
    screen_id = Id.parse(placed["Location"].rstrip("/").rpartition("/")[2])

    current = _fhir("GET", f"/fhir/Appointment/{fhir_id}", token=PATIENT_TOKEN).json()
    asked = current | {"status": "cancelled", "cancelationReason": {"text": REASON}}
    version = f'W/"{current["meta"]["versionId"]}"'
    cancelled = _fhir(
        "PUT", f"/fhir/Appointment/{fhir_id}", asked, token=PATIENT_TOKEN, **{"If-Match": version}
    )
    assert cancelled.status_code == 200, cancelled.json()
    assert cancelled.json()["status"] == "cancelled"
    left = screen.post(f"/portal/appointments/{screen_id}/cancel", {"reason": REASON})
    assert left.status_code == 302, left.content

    audit, notices = _trace(fhir_id)
    assert [e["action"] for e in audit][-1] == "booking.appointment_cancelled"
    assert notices
    assert (audit, notices) == _trace(screen_id)


def test_a_patient_token_sees_neither_the_appointments_nor_the_record_of_another_patient(
    demo: None,
) -> None:
    """Epic E8 Success Evidence: another patient's appointments and Patient stay out of reach."""
    me, other = _user(PATIENT_EMAIL), _user(seed.VISITOR_EMAIL)
    theirs = AppointmentRecord.objects.filter(patient_id=other.value).values_list("id", flat=True)
    assert theirs

    for appointment in theirs:
        read = _fhir("GET", f"/fhir/Appointment/{appointment}", token=PATIENT_TOKEN)
        assert read.status_code == 403
    assert _fhir("GET", f"/fhir/Patient/{other}", token=PATIENT_TOKEN).status_code == 403
    found = _fhir("GET", "/fhir/Appointment?_count=100", token=PATIENT_TOKEN).json()
    patients = {r for e in found.get("entry", []) for r in _references(e["resource"])}
    assert not {f"Patient/{other}"} & patients
    listed = _fhir("GET", "/fhir/Patient?_count=100", token=PATIENT_TOKEN).json()
    assert [e["resource"]["id"] for e in listed.get("entry", [])] == [str(me)]


def _scenario_blocks(stem: str) -> list[str]:
    text = (FEATURES / f"{stem}.feature").read_text()
    return re.split(r"^\s*Scenario(?: Outline)?:", text, flags=re.M)[1:]


def test_every_declared_fhir_write_has_a_scenario_refusing_it_as_the_screen_does() -> None:
    """Epic E8 Success Evidence: each FHIR write shows the screen's or the API's refusal."""
    writes = {(m, r.type) for r in declared() for m, _ in r.routes() if m != "GET"}
    assert set(SAME_REFUSAL) == writes
    for write, (stem, mark) in SAME_REFUSAL.items():
        blocks = [b for b in _scenario_blocks(stem) if mark in b]
        assert blocks, (write, mark)
        assert any(re.search(r"refused|OperationOutcome", b) for b in blocks), write
