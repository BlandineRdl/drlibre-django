import re
from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta

import pytest
from django.conf import settings
from django.test import Client

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.bootstrap.container import real_adapters, use_container, wire
from drlibre.identity.domain.user import Role, User
from tests.builders import PASSWORD, stored_session, stored_user, unique_email
from tests.builders_reporting import real_activity
from tests.fakes.clock import FixedClock
from tests.integration.bookable import SLOT_START, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
PAGES = ("/console/", "/console/audit/", "/console/settings/")


def signed_in(user: User) -> Client:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(user)
    return client


def page(client: Client, url: str) -> str:
    response = client.get(url)
    assert response.status_code == 200
    return response.content.decode()


@pytest.fixture
def at_now() -> Iterator[None]:
    use_container(wire(real_adapters(FixedClock(NOW))))
    yield
    use_container(None)


@pytest.mark.usefixtures("at_now")
def test_the_dashboard_shows_the_figures_days_and_busiest_of_the_chosen_period() -> None:
    """Story tableau de bord : tuiles §13, RDV par jour et top 5 suivent la période choisie."""
    scene = real_activity()
    paris = scene.clinician("Dr Paris", "Europe/Paris", True)
    cayenne = scene.clinician("Dr Cayenne", "America/Cayenne", True)
    for back, hour, clinician in (
        (0, 9, paris),
        (0, 11, paris),
        (3, 9, cayenne),
        (20, 9, cayenne),
        (20, 11, cayenne),
    ):
        day = NOW.date() - timedelta(days=back)
        scene.appointment(clinician, datetime.combine(day, time(hour)), 30, "COMPLETED", "ONLINE")
    admin = signed_in(stored_user(Role.ADMIN))

    month = page(admin, "/console/?range=30")
    today = page(admin, "/console/?range=today")

    assert '<a href="/console/?range=30" aria-current="page">30 jours</a>' in month
    assert "<dt>RDV</dt><dd>5</dd>" in month
    assert "<dt>Part en ligne</dt><dd>100 %</dd>" in month
    assert month.count('<th scope="row">') >= 30
    assert '<span class="bar bar-100" aria-hidden="true"></span> 2' in month
    assert month.index("Dr Cayenne · 3 RDV") < month.index("Dr Paris · 2 RDV")
    assert "<dt>RDV</dt><dd>2</dd>" in today
    assert "Dr Cayenne" not in today


@pytest.mark.usefixtures("at_now")
def test_without_activity_every_ratio_shows_not_available() -> None:
    """Story tableau de bord : sans activité, « n/a » sur chaque ratio et aucun praticien chargé."""
    shown = page(signed_in(stored_user(Role.ADMIN)), "/console/")

    assert shown.count("<dd>n/a</dd>") == 3
    assert "Aucun RDV sur la période" in shown
    assert '<a href="/console/" aria-current="page">Tableau de bord</a>' in shown


def test_the_journal_filters_by_actor_entity_and_day_newest_first_with_correlation_id(
    admin_client: Client,
) -> None:
    """Story journal : entrées filtrées par acteur, entité et jour, plus récentes d'abord."""
    admin, other = stored_user(Role.ADMIN), stored_user(Role.ADMIN)
    for actor, kind, at, corr in (
        (admin, "appointment", NOW, "corr-new"),
        (admin, "appointment", NOW - timedelta(hours=2), "corr-old"),
        (admin, "user", NOW, "corr-user"),
        (other, "appointment", NOW, "corr-other"),
        (admin, "appointment", NOW - timedelta(days=3), "corr-before"),
    ):
        AuditEntryRecord.objects.create(
            actor_id=actor.id.value,
            action="test.done",
            entity_type=kind,
            at=at,
            correlation_id=corr,
        )
    query = f"actor={admin.email.value}&entity_type=appointment&from=2026-11-19&to=2026-11-20"

    shown = page(admin_client, f"/console/audit/?{query}")

    assert shown.count(f"<td>{admin.email.value}</td>") == 2
    assert shown.index("corr-new") < shown.index("corr-old")
    assert not {"corr-user", "corr-other", "corr-before"} & set(re.findall(r"corr-[a-z]+", shown))
    assert "<td>20/11/2026 11:00:00</td>" in shown
    assert "Heures affichées dans le fuseau Europe/Paris." in shown
    assert shown.count('method="post"') == shown.count('action="/sign-out"')


def test_an_unknown_actor_shows_no_entry_and_an_unusable_filter_falls_back_to_the_default(
    admin_client: Client,
) -> None:
    """Story journal : email inconnu → aucune entrée ; filtre inutilisable → journal complet."""
    admin = stored_user(Role.ADMIN)
    AuditEntryRecord.objects.create(
        actor_id=admin.id.value,
        action="test.done",
        entity_type="user",
        correlation_id="corr-x",
        at=NOW,
    )

    unknown = page(admin_client, f"/console/audit/?actor={unique_email('nobody')}")
    unusable = page(admin_client, "/console/audit/?actor=pas-un-email&entity_type=x&from=hier")

    assert "Aucune entrée pour ces filtres." in unknown
    assert "corr-x" in unusable
    assert 'value="pas-un-email"' not in unusable


def test_running_reminders_twice_sends_them_once() -> None:
    """Story réglages : « Lancer les rappels » envoie les rappels dus ; relancé, aucun."""
    with bookable() as world:
        patient = stored_user(Role.PATIENT, password=None)
        world.app().book_appointment.execute(
            patient_id=patient.id,
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
        )
        use_container(world.app(SLOT_START - timedelta(hours=23)))
        try:
            admin = Client()
            admin.post(
                "/sign-in", {"email": stored_user(Role.ADMIN).email.value, "password": PASSWORD}
            )
            first = admin.post("/console/settings/reminders")
            second = admin.post("/console/settings/reminders")
            again = page(admin, second["Location"])
        finally:
            use_container(None)

    sent = int(first["Location"].rsplit("=", 1)[1])
    assert first["Location"].startswith("/console/settings/?done=reminders&count=")
    assert sent >= 1
    assert second["Location"] == "/console/settings/?done=reminders&count=0"
    assert '<p role="status">0 rappel envoyé</p>' in again
    assert "Lancer les rappels" in again


def test_the_settings_show_the_booking_rules() -> None:
    """Story réglages : délai de réservation, d'annulation et limite en ligne affichés."""
    shown = page(signed_in(stored_user(Role.ADMIN)), "/console/settings/")

    assert "<dd>120 min</dd>" in shown
    assert "<dd>24 h</dd>" in shown
    assert "<dd>3</dd>" in shown


def test_a_clinician_is_refused_on_every_supervision_page() -> None:
    """Story supervision : un praticien reçoit 403 sur tableau de bord, journal et réglages."""
    clinician = signed_in(stored_user(Role.CLINICIAN))

    refused = [clinician.get(url).status_code for url in PAGES]

    assert refused == [403, 403, 403]
    assert clinician.post("/console/settings/reminders").status_code == 403
