from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role, User
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.system_clock import SystemClock
from tests.builders import stored_session, stored_user
from tests.builders_booking import StoredScene, existing_appointment, stored_scene

pytestmark = [pytest.mark.integration, pytest.mark.django_db]
COOKIE = settings.SESSION_COOKIE_NAME
URL = "/api/v1/appointments"


def stored(
    scene: StoredScene,
    patient: Id,
    days: int,
    *,
    second: bool = False,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Appointment:
    start = SystemClock().now().replace(microsecond=0) + timedelta(days=days)
    appointment = existing_appointment(
        patient_id=patient,
        clinician_id=scene.clinicians[1 if second else 0].id,
        appointment_type_id=scene.kind,
        start=start,
        end=start + timedelta(minutes=30),
        room_id=scene.room,
        status=status,
        reason="Douleur",
    )
    DjangoAppointments().add(appointment)
    return appointment


def signed_in(client: Client, user: User) -> Client:
    client.cookies[COOKIE] = stored_session(user)
    return client


def listed(response: Any) -> list[str]:
    body = response.json()
    return [entry["id"] for entry in body["upcoming"] + body["past"]]


@pytest.fixture
def scene() -> StoredScene:
    return stored_scene()


def test_a_patient_gets_only_their_own_appointments_even_naming_another_patient(
    client: Client, scene: StoredScene
) -> None:
    """Story « retrouve ses RDV » : seuls ses propres RDV, même s'il nomme un autre patient."""
    patient, other = stored_user(Role.PATIENT), stored_user(Role.PATIENT)
    mine = stored(scene, patient.id, 3)
    stored(scene, other.id, 4)

    response = signed_in(client, patient).get(URL, {"patient": str(other.id)})

    assert response.status_code == 200
    assert listed(response) == [str(mine.id)]
    entry = response.json()["upcoming"][0]
    assert entry["hospital_name"] == "Hôpital Nord"
    assert entry["time_zone"] == "Europe/Paris"
    assert entry["room"] == "Salle 1"
    assert entry["allowed_actions"] == ["cancel", "reschedule"]


def test_a_patient_filters_by_clinician_status_and_period(
    client: Client, scene: StoredScene
) -> None:
    """Story « retrouve ses RDV » : GET /appointments filtre par praticien, statut et période."""
    patient = stored_user(Role.PATIENT)
    first = stored(scene, patient.id, 3)
    second = stored(scene, patient.id, 4, second=True)
    cancelled = stored(scene, patient.id, 5, status=AppointmentStatus.CANCELLED)
    signed_in(client, patient)
    period = {"from": second.start.isoformat(), "to": cancelled.start.isoformat()}

    by_clinician = client.get(URL, {"clinician": str(scene.clinicians[1].id)})
    by_status = client.get(URL, {"status": "CANCELLED"})
    by_period = client.get(URL, period)

    assert listed(by_clinician) == [str(second.id)]
    assert listed(by_status) == [str(cancelled.id)]
    assert listed(by_period) == [str(second.id)]
    assert str(first.id) not in listed(by_period)


def test_an_unusable_filter_is_refused_as_invalid_input(client: Client, scene: StoredScene) -> None:
    """Spec §4 : une valeur invalide est refusée avec le champ en cause."""
    response = signed_in(client, stored_user(Role.PATIENT)).get(URL, {"status": "CONFIRMED"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_input"


def test_an_anonymous_caller_is_unauthenticated(client: Client) -> None:
    """Spec §14 : GET /appointments demande une session."""
    response = client.get(URL)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN], ids=["no-profile", "admin"])
def test_an_admin_or_a_clinician_without_profile_is_forbidden_the_list(
    client: Client, role: Role
) -> None:
    """Plan E6 : la liste sert patients et praticiens ; l'admin attend E7."""
    response = signed_in(client, stored_user(role)).get(URL)

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
