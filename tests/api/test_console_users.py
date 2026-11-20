import pytest
from django.conf import settings
from django.test import Client

from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import ClinicianProfileRecord
from drlibre.organisation.infrastructure.repositories import (
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
    DjangoSpecialties,
)
from tests import builders_organisation as build
from tests.builders import PASSWORD, stored_session, stored_user, unique_email

pytestmark = [pytest.mark.integration, pytest.mark.django_db]
COOKIE = settings.SESSION_COOKIE_NAME


def test_admin_creates_an_account_with_a_lower_case_email_and_finds_it_by_name(
    admin_client: Client,
) -> None:
    """Comptes utilisateurs : email enregistré en minuscules, liste cherchable par nom."""
    email = unique_email("Ana.Bel").replace("ana.bel", "Ana.Bel")

    response = admin_client.post(
        "/console/users/new",
        {
            "full_name": "Ana Bel",
            "email": email,
            "role": "CLINICIAN",
            "active": "on",
            "temporary_password": "temporary-pass-1",
        },
    )

    record = UserRecord.objects.get(email=email.lower())
    assert response["Location"] == "/console/users/?done=created"
    assert record.must_change_password is True
    listing = admin_client.get("/console/users/?search=ana+bel").content.decode()
    assert email.lower() in listing


def test_a_deactivated_user_is_signed_out_on_their_next_request(admin_client: Client) -> None:
    """Story comptes utilisateurs: désactiver un utilisateur coupe ses sessions immédiatement."""
    clinician = stored_user(Role.CLINICIAN)
    their_browser = Client()
    their_browser.post("/sign-in", {"email": clinician.email.value, "password": PASSWORD})
    assert their_browser.get("/workspace/").status_code == 200

    admin_client.post(
        f"/console/users/{clinician.id}/edit",
        {"full_name": clinician.full_name, "email": clinician.email.value, "role": "CLINICIAN"},
    )

    assert their_browser.get("/workspace/")["Location"].startswith("/sign-in")


def test_the_admin_cannot_deactivate_or_delete_their_own_account(client: Client) -> None:
    """Story comptes utilisateurs: ni désactiver, ni supprimer son propre compte."""
    admin = stored_user(Role.ADMIN)
    client.cookies[COOKIE] = stored_session(admin)

    edit = client.post(
        f"/console/users/{admin.id}/edit",
        {"full_name": admin.full_name, "email": admin.email.value, "role": "ADMIN"},
    )
    delete = client.post(f"/console/users/{admin.id}/delete")

    assert edit.status_code == 400
    assert "Vous ne pouvez pas désactiver votre propre compte." in edit.content.decode()
    assert delete.status_code == 403
    assert "Désactivez ce compte" in delete.content.decode()


def test_admin_attaches_a_profile_to_an_active_clinician(admin_client: Client) -> None:
    """Profil praticien : département, spécialité, titre, salle par défaut, poids 1."""
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    specialty = build.specialty()
    DjangoSpecialties().save(specialty)
    room = build.room(department.id)
    DjangoRooms().save(room)
    clinician = stored_user(Role.CLINICIAN)
    assert clinician.full_name in admin_client.get("/console/clinicians/new").content.decode()

    response = admin_client.post(
        "/console/clinicians/new",
        {
            "user_id": str(clinician.id),
            "department_id": str(department.id),
            "specialty_id": str(specialty.id),
            "title": "Dr Demo",
            "default_room_id": str(room.id),
        },
    )

    profile = ClinicianProfileRecord.objects.get(user_id=clinician.id.value)
    assert response["Location"] == "/console/clinicians/?done=created"
    assert (profile.weight, profile.default_room_id) == (1, room.id.value)
    assert "Dr Demo" in admin_client.get("/console/clinicians/").content.decode()


def test_a_clinician_cannot_manage_accounts(client: Client) -> None:
    """Story chaque rôle: un autre rôle voit une page « forbidden »."""
    client.cookies[COOKIE] = stored_session(stored_user(Role.CLINICIAN))

    assert client.get("/console/users/").status_code == 403
    assert client.get("/console/clinicians/new").status_code == 403
