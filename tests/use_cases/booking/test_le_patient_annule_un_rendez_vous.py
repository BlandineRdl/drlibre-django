from django.test import Client
from pytest_bdd import parsers, scenarios, then, when

from tests.fakes.world import FakeWorld
from tests.use_cases.booking.conftest import Scene, mine, open_session, page_text

scenarios("../../features/booking/le_patient_annule_un_rendez_vous.feature")


def cancel_url(scene: Scene) -> str:
    return f"/portal/appointments/{mine(scene).id}/cancel"


@when("the patient opens the cancel page of the appointment")
def opens_cancel_page(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.get(cancel_url(scene))


@then("the page recalls the appointment and asks for the reason")
def recalls_and_asks(scene: Scene) -> None:
    body = page_text(scene)
    assert scene.page.status_code == 200
    assert "lun. 23/11/2026 de 05:00 à 05:30, fuseau America/Martinique" in body
    assert "Claire A" in body
    assert "Dr · Cardiologie" in body
    assert '<label for="field-reason">Motif de l&#x27;annulation</label>' in body
    assert "Confirmer l&#x27;annulation" in body


@when(
    parsers.parse('the patient confirms the cancellation on the page giving the reason "{reason}"')
)
def confirms_on_page(world: FakeWorld, scene: Scene, web: Client, reason: str) -> None:
    open_session(world, web, scene.patient)
    scene.page = web.post(cancel_url(scene), {"reason": reason})


@then("the page is shown again with the error tied to the reason field, focused")
def error_tied_to_reason(scene: Scene) -> None:
    body = page_text(scene)
    assert scene.page.status_code == 400
    assert 'href="#field-reason"' in body
    assert 'aria-invalid="true" aria-describedby="help-reason error-reason" autofocus' in body
    assert '<small id="error-reason" class="field-error">Ce champ est obligatoire.</small>' in body


@then(parsers.parse('the patient lands on their appointments with the message "{message}"'))
def lands_with_message(scene: Scene, web: Client, message: str) -> None:
    assert scene.page.status_code == 302
    listed = web.get(scene.page["Location"])
    assert f'<p role="status" class="notice">{message}</p>' in listed.content.decode()
