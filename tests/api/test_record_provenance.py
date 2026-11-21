import json
from collections.abc import Iterator

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
    VerificationCodeRecord,
    WaitlistEntryRecord,
)
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
from tests.api.test_booking_endpoints import hold_body
from tests.api.test_workspace_pages import book
from tests.api.waitlist_scene import waitlist_scene
from tests.builders import stored_session, stored_user
from tests.integration.bookable import Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


def test_a_record_an_admin_creates_from_the_console_names_the_admin_as_creator() -> None:
    """Spec §3 : un enregistrement créé par un utilisateur connecté porte son créateur."""
    with waitlist_scene() as scene:
        admin = stored_user(Role.ADMIN)
        patient = stored_user(Role.PATIENT, password=None)
        body = {
            "patient_email": patient.email.value,
            "appointment_type_id": str(scene.world.scene.kind),
            "from_date": "2026-11-23",
            "to_date": "2026-11-27",
        }

        done = scene.client(admin).post("/console/waitlist/new", body)

        assert done.status_code == 302
        added = WaitlistEntryRecord.objects.get(patient_id=patient.id.value)
        assert added.created_by == admin.id.value
        assert added.created_at is not None
        assert added.updated_at is not None


def test_a_hold_an_anonymous_visitor_places_names_no_creator(
    client: Client, world: Bookable
) -> None:
    """Spec §3 : sans utilisateur connecté, l'enregistrement n'a pas de créateur."""
    held = client.post(
        "/api/v1/booking/holds", json.dumps(hold_body(world)), content_type="application/json"
    )

    assert held.status_code == 201
    hold = BookingHoldRecord.objects.get(id=held.json()["hold_id"])
    code = VerificationCodeRecord.objects.get(hold=hold)
    assert (hold.created_by, code.created_by) == (None, None)
    assert hold.created_at is not None


def test_cancelling_an_appointment_moves_its_update_time_and_keeps_its_creation(
    world: Bookable,
) -> None:
    """Spec §3 : toute modification, même en lot SQL, met à jour la date de modification."""
    appointment = book(world, "Ana Martin")
    before = AppointmentRecord.objects.get(id=appointment.id.value)
    admin = Client()
    admin.cookies[settings.SESSION_COOKIE_NAME] = stored_session(stored_user(Role.ADMIN))

    done = admin.post(f"/console/appointments/{appointment.id}/cancel", {"reason": "Fermeture"})

    after = AppointmentRecord.objects.get(id=appointment.id.value)
    assert done.status_code == 302
    assert after.status == "CANCELLED"
    assert after.updated_at > before.updated_at
    assert (after.created_at, after.created_by) == (before.created_at, None)
