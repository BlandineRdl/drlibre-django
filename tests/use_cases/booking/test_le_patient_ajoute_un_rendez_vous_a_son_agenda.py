from django.test import Client
from pytest_bdd import parsers, scenarios, then, when

from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import Scene, mine, open_session, page_text

scenarios("../../features/booking/le_patient_ajoute_un_rendez_vous_a_son_agenda.feature")


def calendar_url(scene: Scene) -> str:
    return f"/portal/appointments/{mine(scene).id}.ics"


@then(parsers.parse('the appointment is listed under "{heading}" with its calendar file'))
def listed_with_file(scene: Scene, heading: str) -> None:
    upcoming, past = page_text(scene).split('<h2 id="past-heading">Passés et annulés</h2>')
    part = upcoming if heading == "À venir" else past
    assert f'href="{calendar_url(scene)}"' in part


@when("the patient downloads the calendar file of the appointment")
def downloads(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.get(calendar_url(scene))


@when("someone without a session downloads the calendar file of the appointment")
def downloads_anonymously(scene: Scene, web: Client) -> None:
    scene.page = web.get(calendar_url(scene))


@then(parsers.parse('the event runs from "{start}" to "{end}"'))
def event_runs(scene: Scene, start: str, end: str) -> None:
    assert scene.page.status_code == 200
    assert scene.page["Content-Type"].startswith("text/calendar")
    body = page_text(scene)
    assert f"DTSTART:{start}\r\n" in body
    assert f"DTEND:{end}\r\n" in body
    assert f"UID:{mine(scene).id}" in body


@then(parsers.parse("the download is refused with {status:d}"))
def download_refused(scene: Scene, status: int) -> None:
    assert scene.page.status_code == status
    assert "BEGIN:VCALENDAR" not in page_text(scene)


@then("they are sent to the sign-in page")
def sent_to_sign_in(scene: Scene) -> None:
    assert scene.page.status_code == 302
    assert scene.page["Location"].startswith("/sign-in?")
