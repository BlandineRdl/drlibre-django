"""Steps of the FHIR `Communication` and `AuditEvent` scenarios, checked on portal and audit."""

import json
import re
from datetime import datetime
from string import Template
from typing import Any

from django.conf import settings
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.notifications.infrastructure.django.models import NotificationRecord
from tests.builders import PASSWORD, stored_session
from tests.fhir.appointment_steps import Booking
from tests.fhir.directory_steps import Exchange
from tests.integration.bookable import NOW

_FHIR_JSON = "application/fhir+json"


def _notification(booking: Booking, owner: str, title: str) -> NotificationRecord:
    return NotificationRecord.objects.get(recipient_id=booking.user(owner).id.value, title=title)


def _path(booking: Booking, raw: str) -> str:
    return Template(raw).substitute(booking.values())


def _resources(exchange: Exchange) -> list[dict[str, Any]]:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    return [e["resource"] for e in body.get("entry", ())]


def _listed(raw: str) -> list[str]:
    return sorted(t.strip() for t in raw.split(",") if t.strip())


@when(parsers.re(r'"(?P<who>[^"]+)" searches the communications with "(?P<query>[^"]*)"'))
def searches_communications(booking: Booking, exchange: Exchange, who: str, query: str) -> None:
    path = f"/fhir/Communication?{_path(booking, query)}"
    exchange.response = Client().get(path, headers=booking.headers(who))


@then(parsers.re(r'the communications found are "(?P<titles>[^"]*)"'))
def communications_found(exchange: Exchange, titles: str) -> None:
    found = sorted(r["topic"]["text"] for r in _resources(exchange))
    assert found == _listed(titles)


@then(
    parsers.parse(
        'each communication of "{who}" carries its notification\'s recipient, kind, title, body,'
        " sending, reading and appointment"
    )
)
def communications_carry(booking: Booking, exchange: Exchange, who: str) -> None:
    resources = _resources(exchange)
    records = {
        str(n.id): n
        for n in NotificationRecord.objects.filter(recipient_id=booking.user(who).id.value)
    }
    assert sorted(r["id"] for r in resources) == sorted(records)
    for resource in resources:
        record = records[resource["id"]]
        assert resource["status"] == "completed"
        assert resource["recipient"] == [{"reference": f"Patient/{record.recipient_id}"}]
        assert resource["category"][0]["coding"][0]["code"] == record.kind
        assert resource["topic"]["text"] == record.title
        assert resource["payload"] == [{"contentString": record.body}]
        assert datetime.fromisoformat(resource["sent"]) == record.created_at
        assert "received" not in resource
        assert record.read_at is None
        assert resource["about"] == [{"reference": f"Appointment/{record.appointment_id}"}]


@when(parsers.parse('"{who}" reads the communication "{title}" of "{owner}"'))
def reads_communication(
    booking: Booking, exchange: Exchange, who: str, title: str, owner: str
) -> None:
    found = _notification(booking, owner, title)
    exchange.response = Client().get(
        f"/fhir/Communication/{found.id}", headers=booking.headers(who)
    )


def _put(booking: Booking, who: str, owner: str, title: str, changes: set[str]) -> Any:
    """The owner's current resource with the changes, sent by `who` under its ETag."""
    found = _notification(booking, owner, title)
    path = f"/fhir/Communication/{found.id}"
    current = Client().get(path, headers=booking.headers(owner))
    resource = current.json()
    if "received" in changes:
        resource["received"] = NOW.isoformat()
    if "later" in changes:
        resource["received"] = NOW.replace(hour=NOW.hour + 1).isoformat()
    if "payload" in changes:
        resource["payload"] = [{"contentString": "Un autre texte."}]
    etag = 'W/"stale"' if "stale" in changes else current["ETag"]
    return Client().put(
        path,
        data=json.dumps(resource),
        content_type=_FHIR_JSON,
        headers=booking.headers(who) | {"If-Match": etag},
    )


@when(parsers.parse('"{who}" fills in FHIR the reading of "{title}"'))
def fills_reading(booking: Booking, exchange: Exchange, who: str, title: str) -> None:
    exchange.response = _put(booking, who, who, title, {"received"})


@when(
    parsers.parse('"{who}" sends in FHIR the communication "{title}" of "{owner}" with "{change}"')
)
def sends_change(
    booking: Booking, exchange: Exchange, who: str, title: str, owner: str, change: str
) -> None:
    changes = {c.strip() for c in change.replace(" ", ",").split(",") if c.strip()}
    exchange.response = _put(booking, who, owner, title, changes)


@given("nothing more")
def nothing_more() -> None:
    """The background is the whole scene."""


def _portal(booking: Booking, who: str) -> Client:
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(booking.user(who))
    return client


@given(parsers.parse('"{who}" has read "{title}" on the portal'))
def read_on_portal(booking: Booking, who: str, title: str) -> None:
    found = _notification(booking, who, title)
    response = _portal(booking, who).post(
        f"/portal/notifications/{found.id}/read", headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 302, response.content


@then(
    parsers.parse(
        'the communication "{title}" of "{owner}" reads received at the time of the reading'
    )
)
def received_at_reading(booking: Booking, exchange: Exchange, title: str, owner: str) -> None:
    record = _notification(booking, owner, title)
    assert record.read_at == NOW
    assert datetime.fromisoformat(exchange.body()["received"]) == NOW
    assert exchange.response["ETag"] != ""


@then(parsers.parse('the communication "{title}" of "{owner}" is {state}'))
def is_state(booking: Booking, title: str, owner: str, state: str) -> None:
    record = _notification(booking, owner, title)
    assert (record.read_at is not None) == (state == "read")


@then(parsers.parse('the portal notifications of "{who}" show "{read}" read and "{unread}" unread'))
def portal_shows(booking: Booking, who: str, read: str, unread: str) -> None:
    response = _portal(booking, who).get("/portal/notifications")
    assert response.status_code == 200
    articles = re.findall(
        r'<article class="([^"]*)">(.*?)</article>', response.content.decode(), re.S
    )
    states = {
        title: "unread" in css
        for css, body in articles
        for title in (read, unread)
        if title in body
    }
    assert states == {read: False, unread: True}


@then(parsers.parse('the reading is audited "{action}" by "{who}"'))
def reading_audited(booking: Booking, action: str, who: str) -> None:
    entries = AuditEntryRecord.objects.filter(action=action, actor_id=booking.user(who).id.value)
    assert entries.count() == 1


@when(parsers.parse('"{who}" sends "{method}" to the communications with "{path}"'))
def sends_method(booking: Booking, exchange: Exchange, who: str, method: str, path: str) -> None:
    exchange.response = Client().generic(
        method,
        _path(booking, path),
        data=json.dumps({"resourceType": "Communication", "status": "completed"}),
        content_type=_FHIR_JSON,
        headers=booking.headers(who),
    )


@then("the client is refused with 405 as not supported")
def not_supported(exchange: Exchange) -> None:
    assert exchange.response.status_code == 405
    assert exchange.body()["issue"][0]["code"] == "not-supported"


@given(parsers.parse('"{who}" has signed in on the application API'))
def signed_in(booking: Booking, who: str) -> None:
    response = Client().post(
        "/api/v1/auth/login",
        data=json.dumps({"email": booking.user(who).email.value, "password": PASSWORD}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    booking.asked["correlation"] = response["x-correlation-id"]


@when(parsers.re(r'"(?P<who>[^"]+)" searches the audit events with "(?P<query>[^"]*)"'))
def searches_audit(booking: Booking, exchange: Exchange, who: str, query: str) -> None:
    path = f"/fhir/AuditEvent?{_path(booking, query)}"
    exchange.response = Client().get(path, headers=booking.headers(who))


@then(parsers.re(r'the audit actions found are "(?P<actions>[^"]*)"'))
def audit_found(exchange: Exchange, actions: str) -> None:
    found = sorted(r["subtype"][0]["code"] for r in _resources(exchange))
    assert found == _listed(actions)


def _event(exchange: Exchange, action: str) -> dict[str, Any]:
    (found,) = [r for r in _resources(exchange) if r["subtype"][0]["code"] == action]
    return found


@then(
    parsers.parse(
        'each audit event of "{who}" carries its entry\'s action, time, actor, entity, metadata'
        " and correlation id"
    )
)
def audit_events_carry(booking: Booking, exchange: Exchange, who: str) -> None:
    resources = _resources(exchange)
    records = {
        str(e.id): e for e in AuditEntryRecord.objects.filter(actor_id=booking.user(who).id.value)
    }
    assert sorted(r["id"] for r in resources) == sorted(records)
    for resource in resources:
        record = records[resource["id"]]
        assert resource["action"] == "E"
        assert datetime.fromisoformat(resource["recorded"]) == record.at
        assert resource["agent"] == [
            {"who": {"reference": f"Patient/{record.actor_id}"}, "requestor": True}
        ]
        (entity,) = resource["entity"]
        assert entity["type"]["code"] == record.entity_type
        details = {d["type"]: d["valueString"] for d in entity.get("detail", ())}
        assert details == {
            k: v if isinstance(v, str) else json.dumps(v) for k, v in record.metadata.items()
        }
        extensions = [e["valueString"] for e in resource.get("extension", ())]
        assert extensions == ([record.correlation_id] if record.correlation_id else [])
        assert resource["meta"]["versionId"] == "1"


@then(parsers.parse('the sign-in event names "{reference}" and the correlation id of the sign-in'))
def sign_in_event(booking: Booking, exchange: Exchange, reference: str) -> None:
    event = _event(exchange, "auth.login_succeeded")
    assert event["entity"][0]["what"] == {"reference": _path(booking, reference)}
    assert event["extension"][0]["valueString"] == booking.asked["correlation"]


@then(parsers.parse('the booking event names the appointment of "{who}"'))
def booking_event(booking: Booking, exchange: Exchange, who: str) -> None:
    event = _event(exchange, "booking.appointment_booked")
    assert event["entity"][0]["what"] == {"reference": f"Appointment/{booking.labels[who]}"}


@then("no audit event shows a name or an email beyond the audited metadata")
def no_personal_data(booking: Booking, exchange: Exchange) -> None:
    text = exchange.response.content.decode()
    for person in booking.people.values():
        assert person.email.value not in text
        assert person.full_name not in text


def _sign_in_event(booking: Booking, who: str) -> AuditEntryRecord:
    return AuditEntryRecord.objects.get(
        action="auth.login_succeeded", actor_id=booking.user(who).id.value
    )


@when(parsers.parse('"{who}" reads the sign-in event of "{owner}"'))
def reads_event(booking: Booking, exchange: Exchange, who: str, owner: str) -> None:
    found = _sign_in_event(booking, owner)
    exchange.response = Client().get(f"/fhir/AuditEvent/{found.id}", headers=booking.headers(who))


@when(parsers.parse('"{who}" sends "{method}" to the audit event of "{owner}"'))
def sends_to_event(booking: Booking, exchange: Exchange, who: str, method: str, owner: str) -> None:
    found = _sign_in_event(booking, owner)
    path = "/fhir/AuditEvent" if method == "POST" else f"/fhir/AuditEvent/{found.id}"
    exchange.response = Client().generic(
        method, path, data="{}", content_type=_FHIR_JSON, headers=booking.headers(who)
    )
