import dataclasses
import re
from datetime import UTC, datetime, timedelta

from django.test import Client
from django.urls import resolve
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.interfaces.web.views import search
from drlibre.notifications.domain.notification import AppointmentEvent, Notification
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.conftest import Scene, open_session, page_text

scenarios("../../features/booking/le_patient_voit_son_prochain_rendez_vous_des_l_accueil.feature")

START = datetime(2026, 11, 25, 13, tzinfo=UTC)


@given(parsers.parse("the patient has {unread:d} unread notifications and {read:d} read one"))
def has_notifications(world: FakeWorld, scene: Scene, unread: int, read: int) -> None:
    for index in range(unread + read):
        made = Notification.for_event(
            event=AppointmentEvent.BOOKED,
            recipient_id=scene.patient,
            appointment_id=scene.patient,
            start=START,
            zone_name="Europe/Paris",
            at=world.clock.now() - timedelta(hours=index + 1),
        )
        if index >= unread:
            made = dataclasses.replace(made, read_at=world.clock.now())
        world.notifications.add(made)


@when("the patient opens the home page")
def opens_home(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.get("/portal/")
    assert scene.page.status_code == 200, scene.page.content


@when("the patient marks the first unread notification as read on the notifications page")
def marks_on_page(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    listed = web.get("/portal/notifications").content.decode()
    first = re.findall(r'action="(/portal/notifications/[^"]+/read)"', listed)[0]
    assert web.post(first).status_code == 302


@then(parsers.parse('the home page greets "{name}"'))
def greets(scene: Scene, name: str) -> None:
    assert f"<h1>Bonjour {name}</h1>" in page_text(scene)


@then(parsers.parse('the home page shows only the appointment "{when_}"'))
def shows_next(scene: Scene, when_: str) -> None:
    body = page_text(scene)
    assert body.count('class="card-when"') == 1
    assert f'class="card-when">{when_}<' in body


@then(parsers.parse('the home page says "{text}"'))
def says(scene: Scene, text: str) -> None:
    assert text in page_text(scene)


@then(parsers.parse('the menu says "{label}"'))
def menu_says(scene: Scene, label: str) -> None:
    assert f'<a href="/portal/notifications">{label}</a>' in page_text(scene)


@then(parsers.parse('the action "{label}" leads to the public search'))
def leads_to_search(scene: Scene, label: str) -> None:
    assert f'<a href="/" role="button">{label}</a>' in page_text(scene)
    assert resolve("/").func is search.home
