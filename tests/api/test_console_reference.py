import re

import pytest
from django.conf import settings
from django.test import Client

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from tests.builders import stored_session, stored_user
from tests.builders_organisation import code

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def hospital_fields(code_value: str, **extra: str) -> dict[str, str]:
    return {
        "name": f"Hôpital {code_value}",
        "code": code_value,
        "street": "1 rue de la Paix",
        "postal_code": "59000",
        "city": "Lille",
        "country": "France",
        "phone": "+33 3 20 00 00 00",
        "time_zone": "America/Montreal",
        "active": "on",
        **extra,
    }


def test_admin_chains_hospital_department_room_type_and_specialty(admin_client: Client) -> None:
    h = code("H")
    created = admin_client.post("/console/hospitals/new", hospital_fields(h))
    assert created["Location"] == "/console/hospitals/?done=created"
    hospital = HospitalRecord.objects.get(code=h)

    d = code("D")
    admin_client.post(
        "/console/departments/new", {"hospital_id": str(hospital.id), "name": "Cardio", "code": d}
    )
    department = DepartmentRecord.objects.get(code=d)
    assert department.hospital_id == hospital.id

    r = code("R")
    admin_client.post(
        "/console/rooms/new",
        {
            "department_id": str(department.id),
            "name": "Salle",
            "code": r,
            "floor": "2",
            "capacity": "3",
            "equipment": "ECG, Tapis",
            "active": "on",
        },
    )
    assert RoomRecord.objects.get(code=r).equipment == ["ECG", "Tapis"]

    t = code("T")
    admin_client.post(
        "/console/appointment-types/new",
        {
            "department_id": str(department.id),
            "name": "Consultation",
            "code": t,
            "duration_minutes": "20",
            "buffer_minutes": "0",
            "colour": "#336699",
            "active": "on",
        },
    )
    assert AppointmentTypeRecord.objects.get(code=t).duration_minutes == 20

    s = code("S")
    admin_client.post("/console/specialties/new", {"name": "Cardiologie", "code": s})
    assert SpecialtyRecord.objects.filter(code=s).exists()

    listing = admin_client.get(f"/console/hospitals/?search={h.lower()}").content.decode()
    assert "America/Montreal" in listing
    assert "1 résultat · page 1 sur 1" in listing
    actions = AuditEntryRecord.objects.filter(entity_id=hospital.id).values_list(
        "action", flat=True
    )
    assert list(actions) == ["hospital.created"]


def test_admin_edits_a_hospital_and_the_audit_names_the_changed_fields(
    admin_client: Client,
) -> None:
    h = code("H")
    admin_client.post("/console/hospitals/new", hospital_fields(h))
    hospital = HospitalRecord.objects.get(code=h)

    form = admin_client.get(f"/console/hospitals/{hospital.id}/edit").content.decode()
    assert f'value="{h}"' in form

    admin_client.post(f"/console/hospitals/{hospital.id}/edit", hospital_fields(h, city="Lens"))

    entry = AuditEntryRecord.objects.get(entity_id=hospital.id, action="hospital.updated")
    assert entry.metadata == {"changed": ["city"]}


def test_invalid_field_is_refused_with_focus_on_it(admin_client: Client) -> None:
    response = admin_client.post(
        "/console/hospitals/new", hospital_fields(code("H"), time_zone="Mars/Olympus")
    )

    body = response.content.decode()
    assert response.status_code == 400
    assert 'role="alert"' in body
    assert re.search(r'id="field-time_zone"[^>]*aria-invalid="true"[^>]*autofocus', body)


def test_unusable_page_value_falls_back_to_the_first_page(admin_client: Client) -> None:
    response = admin_client.get("/console/specialties/?page=abc")

    assert response.status_code == 200


def test_hospital_with_departments_cannot_be_deleted(admin_client: Client) -> None:
    h, d = code("H"), code("D")
    admin_client.post("/console/hospitals/new", hospital_fields(h))
    hospital = HospitalRecord.objects.get(code=h)
    admin_client.post(
        "/console/departments/new",
        {"hospital_id": str(hospital.id), "name": "Pédiatrie", "code": d},
    )

    confirm = admin_client.get(f"/console/hospitals/{hospital.id}/delete")
    refused = admin_client.post(f"/console/hospitals/{hospital.id}/delete")

    assert "Cette action est définitive." in confirm.content.decode()
    assert refused.status_code == 409
    assert f"Département : Pédiatrie ({d})" in refused.content.decode()
    assert HospitalRecord.objects.filter(id=hospital.id).exists()


def test_unused_specialty_is_deleted(admin_client: Client) -> None:
    s = code("S")
    admin_client.post("/console/specialties/new", {"name": "Dermatologie", "code": s})
    specialty = SpecialtyRecord.objects.get(code=s)

    response = admin_client.post(f"/console/specialties/{specialty.id}/delete")

    assert response["Location"] == "/console/specialties/?done=deleted"
    assert not SpecialtyRecord.objects.filter(id=specialty.id).exists()


def test_unknown_record_and_unknown_screen_answer_404(admin_client: Client) -> None:
    unknown = admin_client.get("/console/rooms/00000000-0000-4000-8000-000000000000/edit")
    screen = admin_client.get("/console/nothing/")

    assert unknown.status_code == 404
    assert "Page introuvable" in unknown.content.decode()
    assert screen.status_code == 404


def test_clinician_cannot_open_the_console_screens(client: Client) -> None:
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(stored_user(Role.CLINICIAN))

    assert client.get("/console/hospitals/").status_code == 403
    assert client.post("/console/hospitals/new", hospital_fields(code("H"))).status_code == 403
