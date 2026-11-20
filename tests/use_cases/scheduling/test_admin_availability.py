import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.bootstrap.container import Container
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.builders_web import fake_clinician, fake_user, signed_in
from tests.fakes.world import FakeWorld

scenarios(
    "../../features/scheduling/l_admin_voit_le_resume_hebdomadaire_des_disponibilites.feature",
    "../../features/scheduling/l_admin_consulte_le_calendrier_de_la_semaine_d_un_praticien.feature",
)


class Outcome:
    def __init__(self) -> None:
        self.tz = ZoneInfo("Europe/Paris")
        self.users: dict[str, Id] = {}
        self.profiles: dict[str, Id] = {}
        self.admin: Client | None = None
        self.body = ""

    @property
    def console(self) -> Client:
        assert self.admin is not None
        return self.admin


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


def rule_fields(weekday: str, start: str, end: str) -> dict[str, str]:
    return {"weekday": weekday, "start": start, "end": end, "step_minutes": "30"}


def only_rule(world: FakeWorld, outcome: Outcome, name: str) -> Id:
    (found,) = world.availability_queries.rules_of(outcome.profiles[name])
    return found.id


@given(
    parsers.parse(
        'a hospital of time zone "{time_zone}" with the clinicians "{first}" and "{second}"'
    )
)
def clinicians(world: FakeWorld, outcome: Outcome, time_zone: str, first: str, second: str) -> None:
    outcome.tz = ZoneInfo(time_zone)
    department = Id()
    for name in (first, second):
        outcome.users[name], outcome.profiles[name] = Id(), Id()
        fake_clinician(
            world,
            user_id=outcome.users[name],
            profile_id=outcome.profiles[name],
            department_id=department,
            time_zone=time_zone,
            name=name,
        )


@given(parsers.parse('today is "{day}"'))
def today(world: FakeWorld, outcome: Outcome, day: str) -> None:
    world.clock.at = datetime.combine(date.fromisoformat(day), time(8), tzinfo=outcome.tz)


@given("the admin is signed in on the console")
def admin_signed_in(world: FakeWorld, outcome: Outcome, fake_container: Container) -> None:
    admin = fake_user(world, user_id=Id(), role=Role.ADMIN, name="Admin")
    outcome.admin = signed_in(world, admin)


RULE = (
    r'"(?P<name>[^"]+)" (?:saves|saved) a rule on weekday "(?P<weekday>\d)" '
    r'from "(?P<start>[^"]+)" to "(?P<end>[^"]+)"$'
)


@given(parsers.re(RULE))
@when(parsers.re(RULE))
def saves_rule(
    world: FakeWorld, outcome: Outcome, name: str, weekday: str, start: str, end: str
) -> None:
    world.app.save_availability_rule.execute(
        actor=outcome.users[name], rule_id=None, fields=rule_fields(weekday, start, end)
    )


@when(parsers.parse('"{name}" moves that rule to weekday "{weekday}" from "{start}" to "{end}"'))
def moves_rule(
    world: FakeWorld, outcome: Outcome, name: str, weekday: str, start: str, end: str
) -> None:
    world.app.save_availability_rule.execute(
        actor=outcome.users[name],
        rule_id=only_rule(world, outcome, name),
        fields=rule_fields(weekday, start, end),
    )


@when(parsers.parse('"{name}" deletes that rule'))
def deletes_rule(world: FakeWorld, outcome: Outcome, name: str) -> None:
    world.app.delete_availability_rule.execute(
        actor=outcome.users[name], rule_id=only_rule(world, outcome, name)
    )


@given(parsers.parse('"{name}" recorded a time off from "{start}" to "{end}"'))
def records_time_off(world: FakeWorld, outcome: Outcome, name: str, start: str, end: str) -> None:
    world.app.record_time_off.execute(
        actor=outcome.users[name], fields={"start": start, "end": end, "reason": ""}
    )


@given("the admin opened the clinicians list")
@when("the admin opens the clinicians list")
def opens_list(outcome: Outcome) -> None:
    response = outcome.console.get("/console/clinicians/")
    assert response.status_code == 200
    outcome.body = response.content.decode()


@then(parsers.parse('the summary of "{name}" reads "{summary}"'))
def summary_reads(outcome: Outcome, name: str, summary: str) -> None:
    (row,) = [r for r in outcome.body.split("<tr>") if f"<td>{name}</td>" in r]
    assert f"<td>{summary}</td>" in row


@when(parsers.parse('the admin opens the week of "{name}" starting "{day}"'))
def opens_week(outcome: Outcome, name: str, day: str) -> None:
    response = outcome.console.get(f"/console/clinicians/{outcome.profiles[name]}/week?week={day}")
    assert response.status_code == 200
    outcome.body = response.content.decode()


@then(parsers.parse('the week shows "{label}" on "{day}" at "{times}"'))
def week_shows(outcome: Outcome, label: str, day: str, times: str) -> None:
    days = re.findall(r'<abbr title="[^"]*">([^<]+)</abbr>', outcome.body)
    column = days.index(day)
    rows = re.findall(r'<tr><th scope="row">(\d\d:\d\d)</th>(.*?)</tr>', outcome.body)
    found = [at for at, cells in rows if re.findall(r"<td[^>]*>(.*?)</td>", cells)[column] == label]
    assert found == [t.strip() for t in times.split(",")]


@then(parsers.parse('the week shows no "{label}" cell'))
def week_shows_none(outcome: Outcome, label: str) -> None:
    assert f">{label}</td>" not in outcome.body


@then("the week offers no write action")
def no_write_action(outcome: Outcome) -> None:
    main = outcome.body.split("<main", 1)[1].split("</main>", 1)[0]
    assert "<form" not in main
    assert not re.search(r"Modifier|Supprimer|Ajouter|Enregistrer", main)


@then(parsers.parse('the page names the time zone "{time_zone}"'))
def names_time_zone(outcome: Outcome, time_zone: str) -> None:
    assert f"Fuseau : {time_zone}" in outcome.body
