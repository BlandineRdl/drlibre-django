from typing import Any

import pytest
from django.test import Client

from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.api.waitlist_scene import Waiting, waitlist_scene
from tests.builders import stored_user
from tests.integration.bookable import SLOT_START

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def _id(response: Any) -> Id:
    return Id.parse(response.json()["id"])


def post(client: Client, url: str, body: dict[str, Any] | None = None) -> Any:
    return client.post(f"/api/v1{url}", body or {}, content_type="application/json")


def joining(scene: Waiting, **extra: Any) -> dict[str, Any]:
    kind = str(scene.world.scene.kind)
    return {"appointment_type_id": kind, "from_date": "2026-11-23", "to_date": "2026-11-27"} | extra


def test_post_waitlist_applies_the_same_rules_refusing_anonymous_and_clinician_callers() -> None:
    """Story « le patient s'inscrit » : `POST /waitlist` applique les mêmes règles ;
    sans session, `unauthenticated` ; un praticien reçoit `forbidden`."""
    with waitlist_scene() as scene:
        patient = stored_user(Role.PATIENT, password=None)
        other = stored_user(Role.PATIENT, password=None)

        joined = post(scene.client(patient), "/waitlist", joining(scene))
        anonymous = post(Client(), "/waitlist", joining(scene))
        clinician = post(scene.client(stored_user(Role.CLINICIAN)), "/waitlist", joining(scene))
        naming = post(
            scene.client(patient), "/waitlist", joining(scene, patient_email=other.email.value)
        )
        unknown_field = post(scene.client(patient), "/waitlist", joining(scene, end="x"))
        inverted = post(scene.client(patient), "/waitlist", joining(scene, to_date="2026-11-20"))

        assert joined.status_code == 201
        assert (joined.json()["patient"], joined.json()["status"]) == (str(patient.id), "WAITING")
        assert (anonymous.status_code, anonymous.json()["code"]) == (401, "unauthenticated")
        assert (clinician.status_code, clinician.json()["code"]) == (403, "forbidden")
        assert (naming.status_code, naming.json()["code"]) == (403, "forbidden")
        assert (unknown_field.status_code, unknown_field.json()["code"]) == (400, "invalid_input")
        assert inverted.json()["details"]["fields"][0]["field"] == "to_date"


def test_post_waitlist_lets_the_admin_name_the_patient() -> None:
    """Story « l'admin inscrit un patient » : `POST /waitlist` permet à l'admin de nommer
    le patient."""
    with waitlist_scene() as scene:
        other = stored_user(Role.PATIENT, password=None)
        admin = scene.client(stored_user(Role.ADMIN))

        named = post(admin, "/waitlist", joining(scene, patient_email=other.email.value))
        unknown = post(admin, "/waitlist", joining(scene, patient_email="x@example.org"))

        assert named.status_code == 201
        assert named.json()["patient"] == str(other.id)
        assert (unknown.status_code, unknown.json()["code"]) == (404, "not_found")


def test_post_waitlist_accept_applies_the_same_rules_on_the_patients_own_entries_only() -> None:
    """Story « le patient accepte » : `POST /waitlist/{id}/accept` applique les mêmes règles,
    sur les seules entrées du patient ; un praticien reçoit `forbidden`."""
    with waitlist_scene() as scene:
        url = f"/waitlist/{scene.entry.id}/accept"

        stranger = post(scene.client(stored_user(Role.PATIENT, password=None)), url)
        clinician = post(scene.client(stored_user(Role.CLINICIAN)), url)
        accepted = post(scene.client(), url)

        assert (stranger.status_code, stranger.json()["code"]) == (403, "forbidden")
        assert (clinician.status_code, clinician.json()["code"]) == (403, "forbidden")
        assert accepted.status_code == 201
        assert (accepted.json()["start"], accepted.json()["status"]) == (
            SLOT_START.isoformat(),
            "BOOKED",
        )
        booked = DjangoAppointments().get(_id(accepted))
        assert booked is not None
        assert booked.source is Source.ONLINE
        assert scene.stored().status is WaitlistStatus.BOOKED


def test_post_waitlist_accept_applies_the_same_rules_for_the_admin() -> None:
    """Story « l'admin accepte » : `POST /waitlist/{id}/accept` applique les mêmes règles
    pour l'admin."""
    with waitlist_scene() as scene:
        accepted = post(scene.client(stored_user(Role.ADMIN)), f"/waitlist/{scene.entry.id}/accept")

        assert accepted.status_code == 201
        booked = DjangoAppointments().get(_id(accepted))
        assert booked is not None
        assert (booked.patient_id, booked.source) == (scene.patient.id, Source.STAFF)


def test_an_accept_whose_slot_was_taken_fails_in_conflict_and_puts_the_entry_back() -> None:
    """Story « le patient accepte » : créneau pris entre-temps, `conflict`, entrée `WAITING`."""
    with waitlist_scene() as scene:
        scene.world.app().book_appointment.execute(
            patient_id=stored_user(Role.PATIENT, password=None).id,
            appointment_type_id=scene.world.scene.kind,
            clinician_id=scene.world.clinician,
            start=SLOT_START,
        )

        refused = post(scene.client(), f"/waitlist/{scene.entry.id}/accept")

        assert (refused.status_code, refused.json()["code"]) == (409, "conflict")
        assert refused.json()["details"]["resources"]
        assert scene.stored().status is WaitlistStatus.WAITING
