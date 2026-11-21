from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_session, stored_user
from tests.integration.bookable import SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
URL = "/api/v1/appointments"


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


def signed_in(user: User) -> Client:
    client = Client()
    client.cookies[COOKIE] = stored_session(user)
    return client


def post(client: Client, url: str, body: dict[str, Any] | None = None) -> Any:
    return client.post(url, body or {}, content_type="application/json")


def test_the_admin_books_a_type_not_bookable_online_with_a_named_clinician(
    world: Bookable,
) -> None:
    """Story « réserve » : l'admin réserve un type non réservable en ligne, source `STAFF`."""
    AppointmentTypeRecord.objects.filter(id=world.scene.kind.value).update(bookable_online=False)
    patient = stored_user(Role.PATIENT, password=None)
    body = {
        "patient": str(patient.id),
        "type": str(world.scene.kind),
        "clinician": str(world.clinician),
        "start": SLOT_START.isoformat(),
    }

    response = post(signed_in(stored_user(Role.ADMIN)), URL, body)

    assert response.status_code == 201
    stored = DjangoAppointments().get(Id.parse(response.json()["id"]))
    assert stored is not None
    assert (stored.patient_id, stored.clinician_id, stored.source) == (
        patient.id,
        world.clinician,
        Source.STAFF,
    )


def test_the_admin_must_name_the_clinician_to_book(world: Bookable) -> None:
    """Story « réserve » : l'API exige un praticien pour l'admin (invalid_input)."""
    patient = stored_user(Role.PATIENT, password=None)
    body = {
        "patient": str(patient.id),
        "type": str(world.scene.kind),
        "start": SLOT_START.isoformat(),
    }

    refused = post(signed_in(stored_user(Role.ADMIN)), URL, body)

    assert (refused.status_code, refused.json()["code"]) == (400, "invalid_input")
    assert refused.json()["details"]["fields"][0]["field"] == "clinician"


def test_the_admin_runs_the_reminder_job(world: Bookable) -> None:
    """Story « réglages » : POST /jobs/reminders lance les rappels et renvoie leur nombre."""
    response = post(signed_in(stored_user(Role.ADMIN)), "/api/v1/jobs/reminders")

    assert response.status_code == 200
    assert isinstance(response.json()["count"], int)


def test_only_an_admin_runs_the_reminder_job(world: Bookable) -> None:
    """Story « réglages » : un patient ou un praticien qui lance les rappels reçoit forbidden."""
    clinician = DjangoUsers().get(world.scene.clinicians[0].user_id)
    assert clinician is not None
    callers = [signed_in(stored_user(Role.PATIENT)), signed_in(clinician)]

    refused = [post(caller, "/api/v1/jobs/reminders") for caller in callers]
    anonymous = post(Client(), "/api/v1/jobs/reminders")

    assert [(r.status_code, r.json()["code"]) for r in refused] == [(403, "forbidden")] * 2
    assert anonymous.status_code == 401
