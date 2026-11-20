import dataclasses
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.scheduling.application.ports.outbound import AppointmentType, Clinician
from drlibre.scheduling.application.use_cases.find_free_slots import FindFreeSlotsUseCase
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.domain.slot import Slot
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import appointment, rule, time_off
from tests.fakes.world import FakeWorld

scenarios("../../features/scheduling")


class Outcome:
    def __init__(self) -> None:
        self.time_zone = "Europe/Paris"
        self.department = Id()
        self.type = Id()
        self.people: dict[str, Id] = {}
        self.slots: tuple[Slot, ...] = ()
        self.error: DomainError | None = None

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.time_zone)

    def at(self, raw: str) -> datetime:
        return datetime.fromisoformat(raw).replace(tzinfo=self.tz)

    def person(self, name: str) -> Id:
        return self.people.setdefault(name, Id())


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


def refresh(world: FakeWorld, clinician_id: Id) -> None:
    RefreshSlotsUseCase(
        clock=world.clock,
        directory=world.scheduling_directory,
        rules=world.availability_rules,
        time_offs=world.time_offs,
        appointments=world.active_appointments,
        store=world.slots,
    ).execute(clinician_id=clinician_id)


def ask(world: FakeWorld, outcome: Outcome, clinician_id: Id | None, start: str, end: str) -> None:
    use_case = FindFreeSlotsUseCase(
        clock=world.clock, directory=world.scheduling_directory, queries=world.slots
    )
    try:
        outcome.slots = use_case.execute(
            appointment_type_id=outcome.type,
            clinician_id=clinician_id,
            start=outcome.at(start),
            end=outcome.at(end),
        )
    except DomainError as error:
        outcome.error = error


def add_clinician(world: FakeWorld, outcome: Outcome, name: str, department: Id) -> None:
    clinician = Clinician(outcome.person(name), department, outcome.time_zone, active=True)
    world.scheduling_directory.clinicians[clinician.id] = clinician


def hhmm(raw: str) -> time:
    return time.fromisoformat(raw)


@given(parsers.parse('a department in a hospital of time zone "{time_zone}"'))
def department(outcome: Outcome, time_zone: str) -> None:
    outcome.time_zone = time_zone


@given(parsers.parse('an active clinician "{name}" in that department'))
def clinician(world: FakeWorld, outcome: Outcome, name: str) -> None:
    add_clinician(world, outcome, name, outcome.department)


@given(parsers.parse('an active clinician "{name}" in another department'))
def clinician_elsewhere(world: FakeWorld, outcome: Outcome, name: str) -> None:
    add_clinician(world, outcome, name, Id())


@given(
    parsers.parse(
        "an active appointment type of {duration:d} minutes with a {buffer:d}-minute buffer"
    )
)
def appointment_type(world: FakeWorld, outcome: Outcome, duration: int, buffer: int) -> None:
    kind = AppointmentType(outcome.type, outcome.department, duration, buffer, active=True)
    world.scheduling_directory.types[kind.id] = kind


@given("the appointment type is unknown")
def unknown_type(outcome: Outcome) -> None:
    outcome.type = Id()


@given("the appointment type is inactive")
def inactive_type(world: FakeWorld, outcome: Outcome) -> None:
    types = world.scheduling_directory.types
    types[outcome.type] = dataclasses.replace(types[outcome.type], active=False)


@given(parsers.parse('the clinician "{name}" is unknown'))
def unknown_clinician(outcome: Outcome, name: str) -> None:
    outcome.person(name)


@given(parsers.parse('the clinician "{name}" is inactive'))
def inactive_clinician(world: FakeWorld, outcome: Outcome, name: str) -> None:
    clinicians = world.scheduling_directory.clinicians
    clinician_id = outcome.person(name)
    clinicians[clinician_id] = dataclasses.replace(clinicians[clinician_id], active=False)
    refresh(world, clinician_id)


@given(parsers.parse('today is "{day}"'))
def today(world: FakeWorld, outcome: Outcome, day: str) -> None:
    world.clock.at = datetime.combine(date.fromisoformat(day), time(8), tzinfo=outcome.tz)


@given(
    parsers.re(
        r'"(?P<name>[^"]+)" has a rule on weekday (?P<weekday>\d) from "(?P<start>[^"]+)" to '
        r'"(?P<end>[^"]+)" every (?P<step>\d+) minutes(?:, valid from "(?P<valid_from>[^"]+)")?$'
    )
)
def has_rule(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    weekday: str,
    start: str,
    end: str,
    step: str,
    valid_from: str | None,
) -> None:
    clinician_id = outcome.person(name)
    validity = {"valid_from": date.fromisoformat(valid_from)} if valid_from else {}
    world.availability_rules.save(
        rule(
            clinician_id,
            weekday=int(weekday),
            start=hhmm(start),
            end=hhmm(end),
            step_minutes=int(step),
            **validity,
        )
    )
    refresh(world, clinician_id)


@given(
    parsers.parse('"{name}" has a rule every day from "{start}" to "{end}" every {step:d} minutes')
)
def has_daily_rule(
    world: FakeWorld, outcome: Outcome, name: str, start: str, end: str, step: int
) -> None:
    clinician_id = outcome.person(name)
    for weekday in range(7):
        world.availability_rules.save(
            rule(clinician_id, weekday=weekday, start=hhmm(start), end=hhmm(end), step_minutes=step)
        )
    refresh(world, clinician_id)


@when(
    parsers.parse(
        '"{name}" adds a rule on weekday {weekday:d} from "{start}" to "{end}" '
        "every {step:d} minutes"
    )
)
def adds_rule(
    world: FakeWorld, outcome: Outcome, name: str, weekday: int, start: str, end: str, step: int
) -> None:
    clinician_id = outcome.person(name)
    world.availability_rules.save(
        rule(clinician_id, weekday=weekday, start=hhmm(start), end=hhmm(end), step_minutes=step)
    )
    refresh(world, clinician_id)


@when(parsers.parse('"{name}" moves the rule to "{start}" until "{end}"'))
def moves_rule(world: FakeWorld, outcome: Outcome, name: str, start: str, end: str) -> None:
    clinician_id = outcome.person(name)
    (current,) = world.availability_rules.for_clinician(clinician_id)
    world.availability_rules.save(dataclasses.replace(current, start=hhmm(start), end=hhmm(end)))
    refresh(world, clinician_id)


@when(parsers.parse('"{name}" deletes the rule'))
def deletes_rule(world: FakeWorld, outcome: Outcome, name: str) -> None:
    clinician_id = outcome.person(name)
    (current,) = world.availability_rules.for_clinician(clinician_id)
    world.availability_rules.delete(current.id)
    refresh(world, clinician_id)


@given(parsers.parse('"{name}" has no time off'))
def no_time_off(world: FakeWorld, outcome: Outcome, name: str) -> None:
    assert not world.time_offs.for_clinician(outcome.person(name))


@given(parsers.parse('"{name}" is off from "{start}" to "{end}"'))
@when(parsers.parse('"{name}" is off from "{start}" to "{end}"'))
def is_off(world: FakeWorld, outcome: Outcome, name: str, start: str, end: str) -> None:
    clinician_id = outcome.person(name)
    world.time_offs.save(time_off(clinician_id, outcome.at(start), outcome.at(end)))
    refresh(world, clinician_id)


@when(parsers.parse('the time off of "{name}" is deleted'))
def time_off_deleted(world: FakeWorld, outcome: Outcome, name: str) -> None:
    clinician_id = outcome.person(name)
    (current,) = world.time_offs.for_clinician(clinician_id)
    world.time_offs.delete(current.id)
    refresh(world, clinician_id)


@given(parsers.parse('"{name}" has a "{status}" appointment from "{start}" to "{end}"'))
def has_appointment(
    world: FakeWorld, outcome: Outcome, name: str, status: str, start: str, end: str
) -> None:
    clinician_id = outcome.person(name)
    world.active_appointments.rows.append(
        appointment(clinician_id, outcome.at(start), outcome.at(end), status=status)
    )
    refresh(world, clinician_id)


@when(parsers.parse('the appointment of "{name}" becomes "{status}"'))
def appointment_becomes(world: FakeWorld, outcome: Outcome, name: str, status: str) -> None:
    clinician_id = outcome.person(name)
    rows = world.active_appointments.rows
    rows[:] = [(c, p, status if c == clinician_id else s) for c, p, s in rows]
    refresh(world, clinician_id)


@when(parsers.parse('the slots of "{name}" are asked from "{start}" to "{end}"'))
def slots_of(world: FakeWorld, outcome: Outcome, name: str, start: str, end: str) -> None:
    ask(world, outcome, outcome.person(name), start, end)


@when(parsers.parse('the department\'s slots are asked from "{start}" to "{end}"'))
def department_slots(world: FakeWorld, outcome: Outcome, start: str, end: str) -> None:
    ask(world, outcome, None, start, end)


def local(outcome: Outcome, slot: Slot) -> datetime:
    return slot.start.astimezone(outcome.tz)


@then(parsers.re(r'the slots start at "(?P<starts>[^"]*)"'))
def slots_start(outcome: Outcome, starts: str) -> None:
    assert outcome.error is None
    expected = [s.strip() for s in starts.split(",") if s.strip()]
    assert [local(outcome, s).strftime("%H:%M") for s in outcome.slots] == expected


@then("no slot is returned")
def no_slot(outcome: Outcome) -> None:
    assert outcome.error is None
    assert outcome.slots == ()


@then(parsers.parse("{count:d} slots are returned"))
def slot_count(outcome: Outcome, count: int) -> None:
    assert outcome.error is None
    assert len(outcome.slots) == count


@then(parsers.parse("every slot lasts {minutes:d} minutes"))
def every_slot_lasts(outcome: Outcome, minutes: int) -> None:
    assert all(s.end - s.start == timedelta(minutes=minutes) for s in outcome.slots)
    assert all(s.start.tzinfo is UTC for s in outcome.slots)


@then(parsers.parse('the first slot starts at "{start}"'))
def first_slot(outcome: Outcome, start: str) -> None:
    assert outcome.error is None
    assert local(outcome, outcome.slots[0]) == outcome.at(start)
    assert local(outcome, outcome.slots[0]).strftime("%H:%M") == start[-5:]


@then(parsers.parse('the slots run on "{days}"'))
def slots_run_on(outcome: Outcome, days: str) -> None:
    assert outcome.error is None
    found = sorted({local(outcome, s).date().isoformat() for s in outcome.slots})
    assert found == [d.strip() for d in days.split(",")]


@then(parsers.parse('the request is refused as "{code}"'))
def refused(outcome: Outcome, code: str) -> None:
    assert outcome.error is not None
    assert outcome.error.code == code
