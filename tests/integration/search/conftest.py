import dataclasses
import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.bootstrap.container import real_adapters, use_container, wire
from tests.fakes.clock import FixedClock
from tests.integration.search.world import NOW, SearchWorld


@dataclass
class Outcome:
    """What the visitor received: the last response and every body seen."""

    client: Client
    response: Any = None
    bodies: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        assert self.response is not None
        return html.unescape(self.response.content.decode())

    def json(self) -> Any:
        assert self.response is not None
        return self.response.json()


@pytest.fixture
def world() -> SearchWorld:
    return SearchWorld()


@pytest.fixture(autouse=True)
def fixed_clock_app() -> Iterator[None]:
    use_container(wire(dataclasses.replace(real_adapters(), clock=FixedClock(NOW))))
    yield
    use_container(None)


@pytest.fixture
def outcome(client: Client) -> Outcome:
    return Outcome(client)


def _resolve(world: SearchWorld, url: str) -> str:
    def replace(match: re.Match[str]) -> str:
        kind, name = match.group(1), match.group(2)
        found = {
            "id": world.clinicians,
            "hospital": world.hospitals,
            "specialty": world.specialties,
            "type": world.types,
            "department": world.departments,
        }[kind][name]
        return str(found.id)

    return re.sub(r"\[(id|hospital|specialty|type|department):([^\]]+)\]", replace, url)


def _names(items: list[dict[str, Any]]) -> list[str]:
    return [item.get("full_name") or item["name"] for item in items]


def _item(outcome: Outcome, name: str) -> dict[str, Any]:
    return next(i for i in outcome.json()["items"] if (i.get("full_name") or i["name"]) == name)


def _local(raw: str) -> str:
    return raw[:16].replace("T", " ")


def _starts(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


# Givens


@given(parsers.parse('the hospital "{name}" in "{city}" at {lat:f} {lon:f}'))
def _hospital_at(world: SearchWorld, name: str, city: str, lat: float, lon: float) -> None:
    world.hospital(name, city, latitude=lat, longitude=lon)


@given(parsers.parse('the hospital "{name}" in "{city}" without coordinates'))
def _hospital_without(world: SearchWorld, name: str, city: str) -> None:
    world.hospital(name, city)


@given(parsers.parse('the hospital "{name}" in "{city}" in the time zone "{zone}"'))
def _hospital_zone(world: SearchWorld, name: str, city: str, zone: str) -> None:
    world.hospital(name, city, time_zone=zone)


@given(parsers.parse('the hospital "{name}" is inactive'))
def _hospital_inactive(world: SearchWorld, name: str) -> None:
    world.hospitals[name].active = False
    world.hospitals[name].save()


def _offer(
    world: SearchWorld, department: str, hospital: str, kind: str, minutes: int, online: bool
):
    if department not in world.departments:
        world.department(department, hospital)
    world.appointment_type(kind, department, minutes, online=online)


@given(
    parsers.parse(
        'the department "{department}" of "{hospital}" offers "{kind}" of {minutes:d} '
        "minutes online"
    )
)
def _offer_online(world: SearchWorld, department: str, hospital: str, kind: str, minutes: int):
    _offer(world, department, hospital, kind, minutes, True)


@given(
    parsers.parse(
        'the department "{department}" of "{hospital}" offers "{kind}" of {minutes:d} minutes '
        "by phone only"
    )
)
def _offer_phone(world: SearchWorld, department: str, hospital: str, kind: str, minutes: int):
    _offer(world, department, hospital, kind, minutes, False)


@given(parsers.parse('the type "{kind}" is inactive'))
def _type_inactive(world: SearchWorld, kind: str) -> None:
    world.types[kind].active = False
    world.types[kind].save()


@given(parsers.parse('the clinician "{name}" of "{specialty}" in "{department}"'))
def _clinician(world: SearchWorld, name: str, specialty: str, department: str) -> None:
    world.clinician(name, specialty, department)


@given(parsers.parse('the clinician "{name}" is titled "{title}" and presented as "{bio}"'))
def _clinician_title(world: SearchWorld, name: str, title: str, bio: str) -> None:
    world.clinicians[name].title = title
    world.clinicians[name].bio = bio
    world.clinicians[name].save()


@given(parsers.parse('the clinician "{name}" is inactive'))
def _clinician_inactive(world: SearchWorld, name: str) -> None:
    from drlibre.identity.infrastructure.django.models import UserRecord

    UserRecord.objects.filter(id=world.clinicians[name].user_id).update(active=False)


@given(parsers.parse('the specialty "{name}" is inactive'))
def _specialty_inactive(world: SearchWorld, name: str) -> None:
    world.specialties[name].active = False
    world.specialties[name].save()


@given(
    parsers.parse(
        'the clinician "{name}" has the email "{email}", the phone "{phone}" '
        'and the birth date "{birth}"'
    )
)
def _clinician_contact(world: SearchWorld, name: str, email: str, phone: str, birth: str) -> None:
    from datetime import date

    from drlibre.identity.infrastructure.django.models import UserRecord

    UserRecord.objects.filter(id=world.clinicians[name].user_id).update(
        email=email, phone=phone, birth_date=date.fromisoformat(birth)
    )


def _dated(raw: str) -> list[str]:
    """Starts written as dates with times; a bare time keeps the date before it."""
    found, day = [], ""
    for start in _starts(raw):
        if " " in start:
            day = start.split(" ")[0]
        found.append(start if " " in start else f"{day} {start}")
    return found


@given(parsers.parse('"{name}" is free at "{starts}" for "{kind}"'))
def _free_for(world: SearchWorld, name: str, starts: str, kind: str) -> None:
    world.free(name, _dated(starts), kind)


@given(parsers.parse('"{name}" is free at "{starts}"'))
def _free(world: SearchWorld, name: str, starts: str) -> None:
    world.free(name, _dated(starts))


@given(parsers.parse('a hold on "{name}" at "{start}" with {minutes:d} minutes left'))
def _hold(world: SearchWorld, name: str, start: str, minutes: int) -> None:
    world.hold(name, start, minutes_left=minutes)


@given(
    parsers.parse('{count:d} more clinicians named "{prefix}" of "{specialty}" in "{department}"')
)
def _many(world: SearchWorld, count: int, prefix: str, specialty: str, department: str) -> None:
    for number in range(1, count + 1):
        world.clinician(f"{prefix} {number:02}", specialty, department)


@given(parsers.parse('two clinicians both named "{name}" of "{specialty}" in "{department}"'))
def _twins(world: SearchWorld, name: str, specialty: str, department: str) -> None:
    world.clinician(name, specialty, department)
    world.clinician(name, specialty, department)


# When


@when(parsers.parse('the visitor opens "{url}"'))
def _open(world: SearchWorld, outcome: Outcome, url: str) -> None:
    outcome.response = outcome.client.get(_resolve(world, url))
    outcome.bodies.append(outcome.text)


# Then


@then(parsers.parse("the response status is {status:d}"))
def _status(outcome: Outcome, status: int) -> None:
    assert outcome.response is not None
    assert outcome.response.status_code == status, outcome.text[:300]


@then(parsers.parse('the page says "{text}"'))
def _page_says(outcome: Outcome, text: str) -> None:
    assert text in outcome.text, f"{text!r} not in the page"


@then(parsers.parse('the page never says "{text}"'))
def _page_never_says(outcome: Outcome, text: str) -> None:
    assert text not in outcome.text


@then(parsers.parse('the page links to "{target}"'))
def _page_links(world: SearchWorld, outcome: Outcome, target: str) -> None:
    assert f'href="{_resolve(world, target)}"' in outcome.text, [
        h for h in re.findall(r'href="[^"]*"', outcome.text) if "booking" in h
    ]


@then(parsers.parse('no response ever said "{text}"'))
def _never_said(outcome: Outcome, text: str) -> None:
    assert not [body for body in outcome.bodies if text in body]


@then(parsers.parse('the listed names are "{names}"'))
def _listed(outcome: Outcome, names: str) -> None:
    assert _names(outcome.json()["items"]) == _starts(names)


@then("nothing is listed")
def _nothing(outcome: Outcome) -> None:
    assert outcome.json()["items"] == []


@then(parsers.parse('"{name}" shows "{field_name}" equal to "{value}"'))
def _field(outcome: Outcome, name: str, field_name: str, value: str) -> None:
    shown = _item(outcome, name)[field_name]
    text = ", ".join(shown) if isinstance(shown, list) else str(shown)
    assert text == value


@then(parsers.parse('"{name}" shows the next starts "{starts}"'))
def _next_starts(outcome: Outcome, name: str, starts: str) -> None:
    shown = [_local(s) for s in _item(outcome, name)["next_slots"]["starts"]]
    assert shown == _starts(starts)


@then(parsers.parse('"{name}" shows the type "{kind}"'))
def _next_type(outcome: Outcome, name: str, kind: str) -> None:
    assert _item(outcome, name)["next_slots"]["type_name"] == kind


@then(parsers.parse('"{name}" shows the first start "{start}"'))
def _first_start(outcome: Outcome, name: str, start: str) -> None:
    assert _local(_item(outcome, name)["first_slot"]["start"]) == start


@then(parsers.parse('"{name}" shows no availability'))
def _no_availability(outcome: Outcome, name: str) -> None:
    item = _item(outcome, name)
    assert (item.get("next_slots") or item.get("first_slot")) is None


@then(parsers.parse('"{name}" is about {km:d} km away'))
def _distance(outcome: Outcome, name: str, km: int) -> None:
    assert abs(_item(outcome, name)["distance_km"] - km) <= 15


@then(parsers.parse("the response lists {count:d} items on page {page:d} of {pages:d}"))
def _paging(outcome: Outcome, count: int, page: int, pages: int) -> None:
    body = outcome.json()
    assert (len(body["items"]), body["page"], body["pages"]) == (count, page, pages)


@then(parsers.parse("the response counts {total:d} results of {size:d} per page"))
def _counts(outcome: Outcome, total: int, size: int) -> None:
    body = outcome.json()
    assert (body["total"], body["size"]) == (total, size)


@then(parsers.parse('the twins are listed by ascending id for "{name}"'))
def _twins_order(outcome: Outcome, name: str) -> None:
    ids = [i["id"] for i in outcome.json()["items"] if i["full_name"] == name]
    assert len(ids) == 2
    assert ids == sorted(ids)


@then(parsers.parse('the free slots start at "{times}" UTC'))
def _api_slots(outcome: Outcome, times: str) -> None:
    shown = [s["start"][11:16] for s in outcome.json()["slots"]]
    assert shown == _starts(times)


@then(parsers.parse('the code is "{code}"'))
def _error_code(outcome: Outcome, code: str) -> None:
    assert outcome.json()["code"] == code


@then(parsers.parse('the week starts on "{day}"'))
def _week_start(outcome: Outcome, day: str) -> None:
    assert outcome.json()["week_start"] == day


@then(parsers.parse('"{name}" lists the starts "{starts}" for the week'))
def _week_starts(outcome: Outcome, name: str, starts: str) -> None:
    del name
    assert [_local(s) for s in outcome.json()["starts"]] == _starts(starts)


@then(parsers.parse("the zone of every start is {offset}"))
def _zone_offset(outcome: Outcome, offset: str) -> None:
    starts = outcome.json()["items"][0]["next_slots"]["starts"]
    assert all(s.endswith(offset) for s in starts)
