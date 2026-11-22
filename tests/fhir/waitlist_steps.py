"""Steps of the FHIR waitlist scenarios, compared with `POST /api/v1/waitlist` and `/accept`."""

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord, WaitlistEntryRecord
from drlibre.bootstrap.container import container
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from tests.fhir.appointment_steps import PARIS, Booking, _at, _local, _parsed, _participants
from tests.fhir.appointment_update_steps import sends_to_api
from tests.fhir.directory_steps import Exchange

_FHIR_JSON = "application/fhir+json"


def _entry(booking: Booking, patient: str) -> WaitlistEntryRecord:
    return WaitlistEntryRecord.objects.get(patient_id=booking.user(patient).id.value)


def _join_requests(booking: Booking, raw: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The FHIR `waitlist` appointment and the application API body of one join."""
    asked, kind = _parsed(raw), str(booking.world.scene.kind)
    coding = {"system": f"{base_url()}/HealthcareService", "code": kind}
    participants = []
    api: dict[str, Any] = {"appointment_type_id": kind}
    if "patient" in asked:
        patient = booking.user(asked["patient"])
        participants.append({"actor": {"reference": f"Patient/{patient.id}"}})
        api["patient_email"] = patient.email.value
    if "practitioner" in asked:
        practitioner = booking.user(asked["practitioner"]).id
        participants.append({"actor": {"reference": f"Practitioner/{practitioner}"}})
        api["clinician_id"] = str(booking.profile(asked["practitioner"]))
    resource: dict[str, Any] = {
        "resourceType": "Appointment",
        "status": "waitlist",
        "serviceType": [{"coding": [coding]}],
        "requestedPeriod": [{"start": asked["from"], "end": asked["to"]}],
    }
    if participants:
        resource["participant"] = participants
    return resource, api | {"from_date": asked["from"], "to_date": asked["to"]}


@when(parsers.parse('"{who}" joins the waitlist in FHIR with "{raw}"'))
def joins_in_fhir(booking: Booking, exchange: Exchange, who: str, raw: str) -> None:
    resource, api = _join_requests(booking, raw)
    booking.asked = {"who": who, "path": "/api/v1/waitlist", "api": api}
    exchange.response = Client().post(
        "/fhir/Appointment",
        data=json.dumps(resource),
        content_type=_FHIR_JSON,
        headers=booking.headers(who),
    )


def _replayed(booking: Booking, exchange: Exchange) -> None:
    """The application API answers a refusal with the same status, code and details."""
    asked = booking.asked
    replayed = Client().post(
        asked["path"],
        data=json.dumps(asked["api"]) if asked["api"] is not None else None,
        content_type="application/json",
        headers=booking.headers(asked["who"]),
    )
    issue = exchange.body()["issue"][0]
    code = issue["details"]["coding"][0]["code"]
    answer = replayed.json()
    assert (replayed.status_code, answer["code"]) == (exchange.response.status_code, code), answer
    if code != "invalid_input":
        assert json.loads(issue.get("diagnostics", "{}")) == (answer["details"] or {})


@then("the application API answers the same to the same join")
@then("the application API answers the same to the same acceptance")
def api_answers_the_same(booking: Booking, exchange: Exchange) -> None:
    _replayed(booking, exchange)


@then("nobody waits on the waitlist")
def nobody_waits() -> None:
    assert not WaitlistEntryRecord.objects.exists()


def _created(exchange: Exchange, resource_type: str) -> dict[str, Any]:
    body = exchange.body()
    assert exchange.response.status_code == 201, body
    assert body["resourceType"] == resource_type
    assert exchange.response["Location"] == f"{base_url()}/{resource_type}/{body['id']}"
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'
    return body


@then(
    parsers.re(
        r'the waitlist entry of "(?P<patient>[^"]+)" is created "(?P<status>[^"]+)" from'
        r' "(?P<start>[^"]+)" to "(?P<end>[^"]+)" with (?P<preferred>no practitioner|"[^"]+")'
    )
)
def entry_created(
    booking: Booking,
    exchange: Exchange,
    patient: str,
    status: str,
    start: str,
    end: str,
    preferred: str,
) -> None:
    body = _created(exchange, "Appointment")
    entry = _entry(booking, patient)
    assert (body["id"], body["status"]) == (str(entry.id), status)
    assert "start" not in body
    window = body["requestedPeriod"][0]
    after = date.fromisoformat(end) + timedelta(days=1)
    days = [datetime.fromisoformat(window[k]).astimezone(PARIS).date() for k in ("start", "end")]
    assert days == [date.fromisoformat(start), after]
    practitioners = [p for p in _participants(body) if p.startswith("Practitioner/")]
    expected = [] if preferred == "no practitioner" else [preferred.strip('"')]
    assert practitioners == [f"Practitioner/{booking.user(name).id}" for name in expected]
    assert f"Patient/{booking.user(patient).id}" in _participants(body)


@then(parsers.parse('the join is audited "{action}" by "{who}"'))
def join_audited(booking: Booking, exchange: Exchange, action: str, who: str) -> None:
    (entry,) = AuditEntryRecord.objects.filter(entity_id=uuid.UUID(exchange.body()["id"]))
    assert (entry.action, entry.actor_id) == (action, booking.user(who).id.value)


@given("the waitlisted appointment type is inactive")
def type_inactive(booking: Booking) -> None:
    AppointmentTypeRecord.objects.filter(id=booking.world.scene.kind.value).update(active=False)


@given(parsers.parse('the "{clinician}" clinician is inactive'))
def clinician_inactive(booking: Booking, clinician: str) -> None:
    UserRecord.objects.filter(id=booking.user(clinician).id.value).update(active=False)


@given(parsers.parse('"{owner}" has cancelled their appointment on the application API'))
def has_cancelled(booking: Booking, owner: str) -> None:
    sends_to_api(booking, owner, "status=cancelled, reason=Empêchement", owner)


@given("the waitlist expiry has run")
def expiry_ran() -> None:
    assert container().expire_waitlist.execute()


@given(parsers.parse('the waitlist entry of "{patient}" is "{status}"'))
def entry_is(booking: Booking, patient: str, status: str) -> None:
    entry = _entry(booking, patient)
    if status == "WAITING":
        entry.status, entry.offered_appointment_id = status, None
        entry.save()
    assert entry.status == status


@when(parsers.parse('"{who}" reads the waitlist entry of "{patient}"'))
def reads_entry(booking: Booking, exchange: Exchange, who: str, patient: str) -> None:
    path = f"/fhir/Appointment/{_entry(booking, patient).id}"
    exchange.response = Client().get(path, headers=booking.headers(who))


@then(parsers.parse('the entry reads "{status}" with no start'))
def reads_unplaced(exchange: Exchange, status: str) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert (body["status"], "start" in body) == (status, False)


@then(parsers.parse('the entry reads "{status}" from "{start}" to "{end}" with "{clinician}"'))
def reads_placed(
    booking: Booking, exchange: Exchange, status: str, start: str, end: str, clinician: str
) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert (body["status"], _local(body["start"]), _local(body["end"])) == (status, start, end)
    assert f"Practitioner/{booking.user(clinician).id}" in _participants(body)


def _accept(booking: Booking, who: str, patient: str) -> Any:
    entry = _entry(booking, patient).id
    booking.asked = {"who": who, "path": f"/api/v1/waitlist/{entry}/accept", "api": None}
    resource = {
        "resourceType": "AppointmentResponse",
        "appointment": {"reference": f"Appointment/{entry}"},
        "participantStatus": "accepted",
    }
    return Client().post(
        "/fhir/AppointmentResponse",
        data=json.dumps(resource),
        content_type=_FHIR_JSON,
        headers=booking.headers(who),
    )


@when(parsers.parse('"{who}" accepts in FHIR the offer of "{patient}"'))
def accepts_in_fhir(booking: Booking, exchange: Exchange, who: str, patient: str) -> None:
    exchange.response = _accept(booking, who, patient)


@given(parsers.parse('"{who}" has accepted in FHIR the offer of "{patient}"'))
def has_accepted(booking: Booking, who: str, patient: str) -> None:
    response = _accept(booking, who, patient)
    assert response.status_code == 201, response.content


@when(parsers.parse('"{who}" accepts on the application API the offer of "{patient}"'))
def accepts_on_api(booking: Booking, who: str, patient: str) -> None:
    response = Client().post(
        f"/api/v1/waitlist/{_entry(booking, patient).id}/accept",
        headers=booking.headers(who),
    )
    assert response.status_code == 201, response.content


@then(parsers.parse('the response is created "{status}" for "{patient}"'))
def response_created(booking: Booking, exchange: Exchange, status: str, patient: str) -> None:
    body = _created(exchange, "AppointmentResponse")
    entry = _entry(booking, patient).id
    assert (body["id"], body["participantStatus"]) == (str(entry), status)
    assert body["appointment"] == {"reference": f"Appointment/{entry}"}
    assert body["actor"] == {"reference": f"Patient/{booking.user(patient).id}"}


@then(
    parsers.parse(
        'the waitlist entry of "{patient}" is booked with "{clinician}" at "{hhmm}"'
        ' for the source "{source}"'
    )
)
def entry_booked(booking: Booking, patient: str, clinician: str, hhmm: str, source: str) -> None:
    entry = _entry(booking, patient)
    appointment = AppointmentRecord.objects.get(id=entry.id)
    assert entry.status == "BOOKED"
    assert (appointment.status, appointment.source) == ("BOOKED", source)
    assert (appointment.clinician_id, appointment.start) == (
        booking.profile(clinician).value,
        _at(hhmm),
    )


@then(parsers.parse('the appointments of "{patient}" are that one resource only'))
def one_resource(booking: Booking, patient: str) -> None:
    user = booking.user(patient)
    response = Client().get(
        f"/fhir/Appointment?patient=Patient/{user.id}", headers=booking.headers(patient)
    )
    found = [e["resource"] for e in response.json()["entry"]]
    assert [(r["id"], r["status"]) for r in found] == [(str(_entry(booking, patient).id), "booked")]


@when(parsers.parse('"{who}" reads the response of "{patient}"'))
def reads_response(booking: Booking, exchange: Exchange, who: str, patient: str) -> None:
    path = f"/fhir/AppointmentResponse/{_entry(booking, patient).id}"
    exchange.response = Client().get(path, headers=booking.headers(who))


@then(parsers.parse("the client is answered {status:d}"))
def answered(exchange: Exchange, status: int) -> None:
    assert exchange.response.status_code == status, exchange.body()


@when(parsers.parse('"{who}" searches the responses'))
def searches_responses(booking: Booking, exchange: Exchange, who: str) -> None:
    exchange.response = Client().get("/fhir/AppointmentResponse", headers=booking.headers(who))


@then(parsers.re(r'the responses found are "(?P<names>[^"]*)"'))
def responses_found(booking: Booking, exchange: Exchange, names: str) -> None:
    body = exchange.body()
    expected = [str(_entry(booking, n).id) for n in names.split(",") if n]
    assert [e["resource"]["id"] for e in body.get("entry", [])] == expected
    assert body["total"] == len(expected)


def _ids_left_out(value: Any) -> Any:
    """Metadata with ids replaced, so two patients' traces compare."""
    if isinstance(value, dict):
        return {k: _ids_left_out(v) for k, v in value.items()}
    try:
        uuid.UUID(str(value))
    except ValueError:
        return value
    return "<id>"


@then(
    parsers.parse(
        'the acceptances of "{first}" and "{second}" leave alike audit entries, the same'
        " notification and the same email"
    )
)
def alike_acceptances(booking: Booking, first: str, second: str) -> None:
    def trace(who: str) -> tuple[Any, ...]:
        entry = _entry(booking, who).id
        audit = [
            (
                r.action,
                r.entity_type,
                _ids_left_out(r.metadata),
                r.actor_id == booking.user(who).id.value,
            )
            for r in AuditEntryRecord.objects.filter(entity_id=entry).order_by("at", "action")
        ]
        notices = list(
            NotificationRecord.objects.filter(appointment_id=entry).values_list("kind", "title")
        )
        to = (booking.user(who).email.value,)
        subjects = sorted(m.subject for m in booking.world.outbox.queued if m.to == to)
        return audit, notices, subjects

    found = trace(first)
    assert all(found)
    assert found == trace(second)
