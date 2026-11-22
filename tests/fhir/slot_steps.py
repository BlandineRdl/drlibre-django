"""Steps of the FHIR `Slot` scenarios, on PostgreSQL with a fixed clock, shared by two features."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.booking.infrastructure.django.models import AppointmentRecord, BookingHoldRecord
from drlibre.bootstrap.container import container, real_adapters, use_container, wire
from drlibre.identity.domain.user import Role
from drlibre.interfaces.fhir.slot_id import SlotKey, slot_id
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.scheduling.infrastructure.repositories import DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.fakes.clock import FixedClock
from tests.fhir.conftest import token_for
from tests.fhir.directory_steps import Exchange, _matches

PARIS = ZoneInfo("Europe/Paris")
HALF_HOUR = timedelta(minutes=30)


@pytest.fixture
def fixed_clock() -> Iterator[None]:
    yield
    use_container(None)


def _at(day: date, hhmm: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(hhmm), tzinfo=PARIS)


@given(
    parsers.parse(
        'on "{today}" the clinician is held at "{held}", booked at "{booked}" and off at'
        ' "{off}" on "{day}"'
    )
)
def taken_day(
    exchange: Exchange, fixed_clock: None, today: str, held: str, booked: str, off: str, day: str
) -> None:
    assert exchange.directory is not None
    scene, on = exchange.directory, date.fromisoformat(day)
    now = datetime.combine(date.fromisoformat(today), time(10), tzinfo=UTC)
    use_container(wire(real_adapters(FixedClock(now))))
    profile, kind = scene.profile.id.value, scene.online.id.value
    BookingHoldRecord.objects.create(
        clinician_id=profile,
        appointment_type_id=kind,
        start=_at(on, held),
        end=_at(on, held) + HALF_HOUR,
        source="ONLINE",
        full_name="Ana Martin",
        birth_date=date(1990, 5, 17),
        email="ana@example.org",
        expires_at=now + timedelta(minutes=10),
    )
    AppointmentRecord.objects.create(
        patient_id=uuid.uuid4(),
        clinician_id=profile,
        appointment_type_id=kind,
        start=_at(on, booked),
        end=_at(on, booked) + HALF_HOUR,
        status="BOOKED",
        source="ONLINE",
    )
    DjangoTimeOffs().save(
        TimeOff(Id(), scene.profile.id, _at(on, off), _at(on, off) + HALF_HOUR, "Formation")
    )
    container().extend_slot_horizon.execute()


@when(parsers.parse('the client with a patient token searches "{path}"'))
def patient_searches(exchange: Exchange, path: str) -> None:
    token = token_for(stored_user(Role.PATIENT))
    exchange.response = Client().get(
        exchange.path(path), headers={"Authorization": f"Bearer {token}"}
    )


@when("the client searches the same slots again")
def searches_again(exchange: Exchange) -> None:
    exchange.previous = exchange.response
    exchange.response = Client().get(exchange.previous.wsgi_request.get_full_path())


@when("the client reads the first slot")
def reads_first(exchange: Exchange) -> None:
    first = exchange.body()["entry"][0]["resource"]["id"]
    exchange.response = Client().get(f"/fhir/Slot/{first}")


def _local(raw: str) -> str:
    return f"{datetime.fromisoformat(raw).astimezone(PARIS):%H:%M}"


@then(parsers.re(r'the FHIR slots are "(?P<slots>[^"]*)"'))
def slots_are(exchange: Exchange, slots: str) -> None:
    assert all(kind == "Slot" for kind, _ in _matches(exchange))
    found = [
        f"{_local(e['resource']['start'])} {e['resource']['status']}"
        for e in exchange.body().get("entry", [])
        if e["search"]["mode"] == "match"
    ]
    assert found == [s.strip() for s in slots.split(",") if s.strip()]


@then(parsers.parse('every slot is of "{service}" on "{schedule}" with its stable id'))
def slot_fields(exchange: Exchange, service: str, schedule: str) -> None:
    assert exchange.directory is not None
    scene = exchange.directory
    for found in (e["resource"] for e in exchange.body()["entry"]):
        start = datetime.fromisoformat(found["start"]).astimezone(UTC)
        assert found["id"] == slot_id(SlotKey(scene.profile.id, scene.online.id, start))
        assert found["serviceType"][0]["coding"][0]["code"] == exchange.path(service)
        assert found["schedule"]["reference"] == exchange.path(schedule)
        assert found["meta"]["versionId"]


@then("the ids are the same as before")
def same_ids(exchange: Exchange) -> None:
    def ids(response: Any) -> list[str]:
        return [e["resource"]["id"] for e in response.json()["entry"]]

    assert ids(exchange.response) == ids(exchange.previous)


@then(parsers.parse('the answer is a FHIR Slot "{status}"'))
def is_slot(exchange: Exchange, status: str) -> None:
    body = exchange.body()
    assert exchange.response.status_code == 200, body
    assert (body["resourceType"], body["status"]) == ("Slot", status)
    assert exchange.response["ETag"] == f'W/"{body["meta"]["versionId"]}"'


@then(parsers.parse('the bundle includes only "{resource}" "{record}"'))
def includes_only(exchange: Exchange, resource: str, record: str) -> None:
    included = [
        (e["resource"]["resourceType"], e["resource"]["id"])
        for e in exchange.body()["entry"]
        if e["search"]["mode"] == "include"
    ]
    assert included == [(resource, exchange.path(record))]
