import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role, User
from tests.builders import stored_session, stored_user
from tests.builders_booking import existing_appointment
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
HOSTILE = {"Origin": "https://evil.example"}
WEEK = "2026-11-23"


@dataclass
class Portal:
    world: Bookable
    patient: User
    appointment: Appointment
    client: Client

    @property
    def base(self) -> str:
        return f"/portal/appointments/{self.appointment.id}"

    def stored(self) -> Appointment:
        found = DjangoAppointments().get(self.appointment.id)
        assert found is not None
        return found


@pytest.fixture
def portal() -> Iterator[Portal]:
    """A passwordless patient booked on Monday 09:00 Paris, signed in, the clock on NOW."""
    with bookable() as world:
        use_container(world.app())
        patient = stored_user(Role.PATIENT, password=None)
        booked = world.app().book_appointment.execute(
            patient_id=patient.id,
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
        )
        client = Client()
        client.cookies[COOKIE] = stored_session(patient)
        yield Portal(world, patient, booked, client)
        use_container(None)


def page(response: object) -> str:
    return response.content.decode()  # type: ignore[attr-defined]


def test_every_portal_page_renders_for_a_passwordless_patient(portal: Portal) -> None:
    """§8 : chaque page du portail s'affiche pour un patient sans mot de passe."""
    urls = (
        "/portal/",
        "/portal/appointments",
        f"{portal.base}/cancel",
        f"{portal.base}/reschedule?week={WEEK}",
        "/portal/notifications",
        "/portal/profile",
    )

    responses = {url: portal.client.get(url) for url in urls}

    assert {url: r.status_code for url, r in responses.items()} == dict.fromkeys(urls, 200)
    assert all("/account/password" not in page(r) for r in responses.values())
    assert 'href="/portal/notifications">Notifications (1 non lue)</a>' in page(
        responses["/portal/"]
    )


def test_cancelling_with_a_reason_moves_it_to_the_past_and_raises_the_unread_count(
    portal: Portal,
) -> None:
    """Story « annule » : boîte de confirmation, CANCELLED, notification « RDV annulé »."""
    done = portal.client.post(f"{portal.base}/cancel", {"reason": "Empêchement"})
    listed = page(portal.client.get(done["Location"]))

    assert done["Location"] == "/portal/appointments?done=cancelled"
    assert '<p role="status" class="notice">Le rendez-vous est annulé.</p>' in listed
    assert "Notifications (2 non lues)" in listed
    _, past = listed.split('<h2 id="past-heading">Passés</h2>')
    assert f'href="{portal.base}.ics"' in past
    assert f'href="{portal.base}/cancel"' not in listed
    assert portal.stored().cancellation_reason == "Empêchement"


def test_marking_a_notification_as_read_lowers_the_unread_count(portal: Portal) -> None:
    """Story « accueil » : le nombre baisse quand une notification est marquée comme lue."""
    listed = page(portal.client.get("/portal/notifications"))
    (mark,) = re.findall(r'action="(/portal/notifications/[^"]+/read)"', listed)

    portal.client.post(mark)
    home = page(portal.client.get("/portal/"))

    assert "Aucune notification non lue." in home
    assert "Lue" in page(portal.client.get("/portal/notifications"))


def test_the_week_strip_offers_the_clinicians_free_slots_and_moves_the_appointment(
    portal: Portal,
) -> None:
    """Story « déplace » : bandeau à la semaine du même praticien, fin recalculée."""
    strip = page(portal.client.get(f"{portal.base}/reschedule?week={WEEK}"))

    assert "Semaine du lun. 23/11 au dim. 29/11" in strip
    assert 'name="start" value="2026-11-23T08:30:00Z"' in strip
    assert ">09:30</button>" in strip

    done = portal.client.post(
        f"{portal.base}/reschedule", {"week": WEEK, "start": "2026-11-23T08:30:00Z"}
    )

    assert done["Location"] == "/portal/appointments?done=moved"
    moved = portal.stored()
    assert (moved.start, moved.end) == (
        SLOT_START + timedelta(minutes=30),
        SLOT_START + timedelta(minutes=60),
    )


def test_the_week_strip_offers_only_slots_starting_at_least_120_minutes_ahead(
    portal: Portal,
) -> None:
    """Story « déplace » : le bandeau ne propose pas un créneau que la règle des 120 min refuse."""
    use_container(portal.world.app(at=SLOT_START - timedelta(minutes=90)))

    strip = page(portal.client.get(f"{portal.base}/reschedule?week={WEEK}"))

    assert 'name="start" value="2026-11-23T08:00:00Z"' not in strip
    assert 'name="start" value="2026-11-23T08:30:00Z"' in strip


def test_late_on_sunday_the_current_week_offers_no_slot_and_leads_to_the_next_week(
    portal: Portal,
) -> None:
    """Story « déplace » : dimanche 22:30 à Paris, semaine en cours vide, la suivante s'ouvre."""
    use_container(portal.world.app(at=datetime(2026, 11, 22, 21, 30, tzinfo=UTC)))

    current = portal.client.get(f"{portal.base}/reschedule?week=2026-11-16")

    assert current.status_code == 200
    assert "Aucun créneau libre cette semaine." in page(current)
    assert f"{portal.base}/reschedule?week={WEEK}" in page(current)
    following = page(portal.client.get(f"{portal.base}/reschedule?week={WEEK}"))
    assert "Semaine du lun. 23/11 au dim. 29/11" in following


def test_a_refused_move_shows_the_strip_again_with_the_broken_rule(portal: Portal) -> None:
    """Story « déplace » : refus en rule_violation affiché avec ses règles, RDV inchangé."""
    refused = portal.client.post(
        f"{portal.base}/reschedule", {"week": WEEK, "start": "2026-11-23T08:15:00Z"}
    )

    body = page(refused)
    assert refused.status_code == 422
    assert "Le déplacement enfreint une règle." in body
    assert "<li>ce créneau n&#x27;est pas libre</li>" in body
    assert 'value="2026-11-23T08:30:00Z"' in body
    assert portal.stored().start == SLOT_START


def test_the_week_strip_stays_within_the_slot_horizon(portal: Portal) -> None:
    """§5 : le bandeau s'ouvre sur la semaine du RDV et ne sort pas de l'horizon des créneaux."""
    strip = page(portal.client.get(f"{portal.base}/reschedule?week=2030-01-07"))
    opened = page(portal.client.get(f"{portal.base}/reschedule"))

    assert "Semaine du lun. 23/11 au dim. 29/11" in opened

    assert "Semaine du lun. 16/11 au dim. 22/11" in strip
    assert "Semaine précédente" not in strip
    assert f"{portal.base}/reschedule?week=2026-11-23" in strip


def test_an_appointment_under_24_hours_offers_no_change_and_the_api_refuses_it(
    portal: Portal,
) -> None:
    """Stories « annule » et « déplace » : moins de 24 h, ni « Annuler » ni « Déplacer »."""
    soon = existing_appointment(
        patient_id=portal.patient.id,
        clinician_id=portal.world.scene.clinicians[1].id,
        appointment_type_id=portal.world.scene.kind,
        start=NOW + timedelta(hours=3),
        end=NOW + timedelta(hours=3, minutes=30),
    )
    DjangoAppointments().add(soon)
    base = f"/portal/appointments/{soon.id}"

    listed = page(portal.client.get("/portal/appointments"))
    refused = portal.client.post(
        f"/api/v1/appointments/{soon.id}/cancel",
        {"reason": "Empêchement"},
        content_type="application/json",
    )

    assert f'href="{base}.ics"' in listed
    assert f'href="{base}/cancel"' not in listed
    assert f'href="{base}/reschedule"' not in listed
    assert f'href="{portal.base}/cancel"' in listed
    assert refused.status_code == 422
    assert refused.json()["details"]["rules"] == ["cancellation_window_closed"]


def test_another_patients_appointment_pages_and_calendar_file_are_forbidden(
    portal: Portal,
) -> None:
    """Story « agenda » : un patient ne télécharge que ses propres RDV."""
    stranger = Client()
    stranger.cookies[COOKIE] = stored_session(stored_user(Role.PATIENT, password=None))

    statuses = [
        stranger.get(url).status_code
        for url in (f"{portal.base}.ics", f"{portal.base}/cancel", f"{portal.base}/reschedule")
    ]

    assert statuses == [403, 403, 403]
    assert portal.client.get(f"{portal.base}.ics").status_code == 200


def test_staff_cannot_open_the_patient_portal(portal: Portal) -> None:
    clinician = Client()
    clinician.cookies[COOKIE] = stored_session(stored_user(Role.CLINICIAN))

    assert clinician.get("/portal/appointments").status_code == 403


def test_a_cross_origin_post_to_the_portal_or_the_api_changes_nothing(portal: Portal) -> None:
    """Règle §12.3 : un POST venu d'un autre site est refusé."""
    web = portal.client.post(f"{portal.base}/cancel", {"reason": "x"}, headers=HOSTILE)
    api = portal.client.post(
        f"/api/v1/appointments/{portal.appointment.id}/cancel",
        {"reason": "x"},
        content_type="application/json",
        headers=HOSTILE,
    )

    assert web.status_code == api.status_code == 403
    assert portal.stored().status is AppointmentStatus.BOOKED


def test_the_cancel_form_rejects_a_post_without_its_csrf_token(portal: Portal) -> None:
    """Règle §12.3 : les formulaires web gardent la protection CSRF."""
    strict = Client(enforce_csrf_checks=True)
    strict.cookies[COOKIE] = portal.client.cookies[COOKIE].value

    refused = strict.post(f"{portal.base}/cancel", {"reason": "Empêchement"})

    assert refused.status_code == 403
    assert portal.stored().status is AppointmentStatus.BOOKED
