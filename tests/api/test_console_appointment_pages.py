import csv
import io
from collections.abc import Iterator
from datetime import timedelta

import pytest
from django.conf import settings
from django.http import StreamingHttpResponse
from django.test import Client

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from drlibre.shared_kernel.ids import Id
from tests.api.test_workspace_pages import book, clinician_client, named_patient
from tests.builders import stored_session, stored_user
from tests.integration.bookable import SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
URL = "/console/appointments/"


@pytest.fixture
def world() -> Iterator[Bookable]:
    with bookable() as world:
        use_container(world.app())
        yield world
        use_container(None)


@pytest.fixture
def admin() -> Client:
    client = Client()
    client.cookies[COOKIE] = stored_session(stored_user(Role.ADMIN))
    return client


def test_the_admin_filters_the_list_and_each_row_names_its_time_zone(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin liste les RDV » : filtres combinés, total, fuseau de l'hôpital nommé."""
    kept = book(world, "Ana Martin")
    book(world, "Léo Durand", SLOT_START + timedelta(minutes=30), index=1)
    query = {"clinician": str(world.clinician), "status": "BOOKED", "department": "inconnu"}

    response = admin.get(URL, query)

    html = response.content.decode()
    assert response.status_code == 200
    assert "1 résultat · page 1 sur 1" in html
    assert "Ana Martin" in html
    assert "Léo Durand" not in html
    assert "23/11/2026 09:00 (Europe/Paris)" in html
    assert f"{URL}{kept.id}" in html
    assert f"export.csv?clinician={world.clinician}&amp;status=BOOKED" in html
    assert 'aria-current="page">Rendez-vous' in html


def test_the_export_is_the_whole_filtered_set_without_names_and_is_audited(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin exporte » : CSV de tout l'ensemble filtré, ids seulement, audité."""
    first = book(world, "Ana Martin")
    book(world, "Léo Durand", SLOT_START + timedelta(minutes=30))
    book(world, "Zoé Blanc", SLOT_START + timedelta(hours=1), index=1)

    response = admin.get(f"{URL}export.csv", {"clinician": str(world.clinician)})

    assert isinstance(response, StreamingHttpResponse)
    body = response.getvalue().decode()
    lines = list(csv.reader(io.StringIO(body)))
    assert response["Content-Type"].startswith("text/csv")
    assert lines[0][:3] == ["appointment_id", "start", "end"]
    assert len(lines) == 3
    assert [str(first.id), "2026-11-23T08:00:00+00:00"] == lines[2][:2]
    assert "Ana Martin" not in body
    assert "Douleur" not in body
    exported = AuditEntryRecord.objects.filter(action="booking.appointments_exported")
    assert [e.metadata for e in exported] == [{"count": 2}]


def test_the_admin_checks_in_then_sees_an_impossible_change_refused_inline(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin change le statut » : arrivé, puis absent refusé en ligne."""
    appointment = book(world, "Ana Martin")
    base = f"{URL}{appointment.id}"

    checked_in = admin.post(f"{base}/check-in")
    shown = admin.get(checked_in["Location"])
    refused = admin.post(f"{base}/no-show")

    assert checked_in.status_code == 302
    assert "Le patient est noté arrivé." in shown.content.decode()
    assert refused.status_code == 409
    assert "Statut actuel : Arrivé." in refused.content.decode()
    stored = DjangoAppointments().get(appointment.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.CHECKED_IN


def test_the_admin_cancels_with_a_reason_the_reason_being_required(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin annule » : motif exigé, puis RDV annulé."""
    appointment = book(world, "Ana Martin")
    url = f"{URL}{appointment.id}/cancel"

    form = admin.get(url)
    missing = admin.post(url, {"reason": "  "})
    done = admin.post(url, {"reason": "Fermeture"})

    assert form.status_code == 200
    assert missing.status_code == 400
    assert done.status_code == 302
    stored = DjangoAppointments().get(appointment.id)
    assert stored is not None
    assert (stored.status, stored.cancellation_reason) == (AppointmentStatus.CANCELLED, "Fermeture")


def test_the_admin_moves_an_appointment_from_the_week_strip(world: Bookable, admin: Client) -> None:
    """Story « l'admin déplace » : bande de la semaine, créneau pris refusé en ligne."""
    appointment = book(world, "Ana Martin")
    other = book(world, "Léo Durand", SLOT_START + timedelta(hours=1))
    base = f"{URL}{appointment.id}"

    page = admin.get(base, {"week": "2026-11-23"})
    taken = admin.post(f"{base}/reschedule", {"start": other.start.isoformat()})
    moved = admin.post(f"{base}/reschedule", {"start": "2026-11-23T10:00:00Z"})

    assert "Déplacer" in page.content.decode()
    assert taken.status_code in (409, 422)
    assert 'role="alert"' in taken.content.decode()
    assert moved.status_code == 302
    stored = DjangoAppointments().get(appointment.id)
    assert stored is not None
    assert stored.start == SLOT_START + timedelta(hours=2)


def test_the_admin_books_a_type_not_bookable_online_through_the_wizard(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin réserve » : patient par nom, type hors ligne, praticien, créneau, salle."""
    AppointmentTypeRecord.objects.filter(id=world.scene.kind.value).update(bookable_online=False)
    patient = named_patient("Inès Moreau")
    choice = {"q": "Inès", "patient": str(patient.id), "type": str(world.scene.kind)}
    book_url = f"{URL}book"

    found = admin.get(book_url, {"q": "Inès"}).content.decode()
    typed = admin.get(book_url, choice).content.decode()
    slots = admin.get(
        book_url, {**choice, "clinician": str(world.clinician), "week": "2026-11-23"}
    ).content.decode()
    booked = admin.post(
        book_url,
        {
            **choice,
            "clinician": str(world.clinician),
            "room": str(world.scene.room),
            "start": "2026-11-23T09:00:00Z",
        },
    )

    assert "Inès Moreau" in found
    assert str(world.clinician) in typed
    assert "Réserver à 10:00" in slots
    assert booked.status_code == 302
    stored = DjangoAppointments().get(Id.parse(booked["Location"].split("/")[3].split("?")[0]))
    assert stored is not None
    assert (stored.patient_id, stored.source, stored.room_id) == (
        patient.id,
        Source.STAFF,
        world.scene.room,
    )


def test_a_wizard_booking_outside_availability_is_refused_inline(
    world: Bookable, admin: Client
) -> None:
    """Story « l'admin réserve » : un créneau hors disponibilité est refusé en ligne."""
    patient = named_patient("Inès Moreau")
    body = {
        "patient": str(patient.id),
        "type": str(world.scene.kind),
        "clinician": str(world.clinician),
        "start": "2026-11-23T18:00:00Z",
    }

    refused = admin.post(f"{URL}book", body)

    assert refused.status_code == 422
    assert 'role="alert"' in refused.content.decode()


def test_a_clinician_cannot_open_the_console_appointments(world: Bookable) -> None:
    """Spec §10 : la console des RDV est réservée à l'admin (403)."""
    response = clinician_client(world).get(URL)

    assert response.status_code == 403
