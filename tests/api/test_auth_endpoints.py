import pytest
from django.conf import settings
from django.test import Client

from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.django.models import SessionRecord
from tests.builders import PASSWORD, deactivated, stored_session, stored_user, unique_email

pytestmark = [pytest.mark.integration, pytest.mark.django_db]
COOKIE = settings.SESSION_COOKIE_NAME


def sign_in(client: Client, email: str, password: str = PASSWORD, **extra: str):
    return client.post("/sign-in", {"email": email, "password": password, **extra})


@pytest.mark.parametrize(
    ("role", "home"),
    [(Role.ADMIN, "/console/"), (Role.CLINICIAN, "/workspace/"), (Role.PATIENT, "/portal/")],
)
def test_each_role_lands_on_its_home(client: Client, role: Role, home: str) -> None:
    user = stored_user(role)

    response = sign_in(client, user.email.value.upper())

    assert response.status_code == 302
    assert response["Location"] == home
    cookie = response.cookies[COOKIE]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert client.get(home).status_code == 200


def test_unknown_email_and_wrong_password_answer_the_same(client: Client) -> None:
    user = stored_user(Role.ADMIN)

    wrong = sign_in(client, user.email.value, "wrong-password-1")
    unknown = sign_in(client, unique_email("nobody"))

    assert wrong.status_code == unknown.status_code == 401
    assert "Email ou mot de passe incorrect." in wrong.content.decode()
    assert "Email ou mot de passe incorrect." in unknown.content.decode()
    assert COOKIE not in wrong.cookies


def test_inactive_user_cannot_sign_in(client: Client) -> None:
    user = stored_user(Role.CLINICIAN, active=False)

    assert sign_in(client, user.email.value).status_code == 401


def test_next_inside_the_role_area_is_kept(client: Client) -> None:
    user = stored_user(Role.ADMIN)

    response = sign_in(client, user.email.value, next="/console/hospitals/")

    assert response["Location"] == "/console/hospitals/"


def test_anonymous_user_is_sent_to_sign_in(client: Client) -> None:
    response = client.get("/console/")

    assert response.status_code == 302
    assert response["Location"] == "/sign-in?next=%2Fconsole%2F"


def test_another_role_area_answers_forbidden(client: Client) -> None:
    sign_in(client, stored_user(Role.CLINICIAN).email.value)

    response = client.get("/console/")

    assert response.status_code == 403
    assert "Accès refusé" in response.content.decode()


def test_deactivated_user_is_signed_out_at_once(client: Client) -> None:
    user = stored_user(Role.ADMIN)
    sign_in(client, user.email.value)

    deactivated(user)

    assert client.get("/console/")["Location"].startswith("/sign-in")


def test_api_login_sets_the_cookie_and_logout_deletes_the_session(client: Client) -> None:
    user = stored_user(Role.CLINICIAN)

    login = client.post(
        "/api/v1/auth/login",
        {"email": user.email.value, "password": PASSWORD},
        content_type="application/json",
    )

    assert login.status_code == 200
    assert login.json() == {"role": "CLINICIAN", "home": "/workspace/"}
    assert login.cookies[COOKIE]["httponly"] is True
    assert SessionRecord.objects.filter(user_id=user.id.value).count() == 1

    logout = client.post("/api/v1/auth/logout")

    assert logout.status_code == 204
    assert not SessionRecord.objects.filter(user_id=user.id.value).exists()
    assert client.get("/workspace/").status_code == 302


def test_api_login_refusal_and_unknown_fields(client: Client) -> None:
    refused = client.post(
        "/api/v1/auth/login",
        {"email": unique_email("nobody"), "password": PASSWORD},
        content_type="application/json",
    )
    extra = client.post(
        "/api/v1/auth/login",
        {"email": "a@example.org", "password": PASSWORD, "role": "ADMIN"},
        content_type="application/json",
    )

    assert refused.status_code == 401
    assert refused.json()["code"] == "unauthenticated"
    assert extra.status_code == 400
    assert extra.json()["code"] == "invalid_input"


def test_temporary_password_must_be_changed_before_the_area(client: Client) -> None:
    user = stored_user(Role.ADMIN, must_change=True)
    sign_in(client, user.email.value)

    assert client.get("/console/")["Location"] == "/account/password"

    bad = client.post(
        "/account/password", {"current_password": "wrong-password-1", "new_password": "x" * 12}
    )
    body = bad.content.decode()
    assert bad.status_code == 400
    assert 'id="field-current_password"' in body
    assert 'aria-invalid="true" aria-describedby="error-current_password" autofocus' in body

    done = client.post(
        "/account/password", {"current_password": PASSWORD, "new_password": "my-own-password"}
    )
    assert done["Location"] == "/console/"
    assert client.get("/console/").status_code == 200


def test_patient_without_password_cannot_change_one(client: Client) -> None:
    patient = stored_user(Role.PATIENT, password=None)
    client.cookies[COOKIE] = stored_session(patient)

    portal = client.get("/portal/").content.decode()
    profile = client.get("/portal/profile").content.decode()

    assert f"<h1>Bonjour {patient.full_name}</h1>" in portal
    assert "/account/password" not in portal + profile
    assert client.get("/account/password").status_code == 403


def test_sign_out_deletes_the_session(client: Client) -> None:
    user = stored_user(Role.ADMIN)
    sign_in(client, user.email.value)

    response = client.post("/sign-out")

    assert response["Location"] == "/sign-in"
    assert not SessionRecord.objects.filter(user_id=user.id.value).exists()
