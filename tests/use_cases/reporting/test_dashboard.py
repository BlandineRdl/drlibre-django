from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.identity.domain.user import Role
from drlibre.reporting.domain.available_minutes import Absence, RuleHours
from drlibre.reporting.domain.dashboard import Dashboard, Range
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders_web import fake_user
from tests.fakes.reporting import ActivityAppointment, ActivityClinician
from tests.fakes.world import FakeWorld

scenarios(
    "../../features/reporting/l_admin_suit_les_indicateurs_du_tableau_de_bord.feature",
    "../../features/reporting/l_admin_voit_les_rdv_par_jour_et_les_praticiens_les_plus_charges.feature",
)

VALID_FROM = datetime(2026, 1, 1).date()


class Outcome:
    def __init__(self) -> None:
        self.clinicians: dict[str, Id] = {}
        self.admin = Id()
        self.patient = Id()
        self.dashboard: Dashboard | None = None
        self.error: DomainError | None = None

    @property
    def shown(self) -> Dashboard:
        assert self.dashboard is not None
        return self.dashboard


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


def add_clinician(world: FakeWorld, outcome: Outcome, name: str, zone: str, *, active: bool) -> Id:
    clinician = Id()
    outcome.clinicians[name] = clinician
    world.activity.clinicians[clinician] = ActivityClinician(time_zone=zone, active=active)
    return clinician


def add_appointment(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    local: datetime,
    minutes: int,
    status: str,
    source: str,
) -> None:
    clinician = outcome.clinicians[name]
    zone = world.activity.clinicians[clinician].time_zone
    start = local.replace(tzinfo=ZoneInfo(zone))
    world.activity.appointments.append(
        ActivityAppointment(
            clinician, name, zone, start, start + timedelta(minutes=minutes), status, source
        )
    )


@given(parsers.parse('now is "{instant}"'))
def now_is(world: FakeWorld, instant: str) -> None:
    world.clock.at = datetime.fromisoformat(instant)


@given(parsers.parse('the clinician "{name}" works in "{zone}"'))
def clinician_in(world: FakeWorld, outcome: Outcome, name: str, zone: str) -> None:
    add_clinician(world, outcome, name, zone, active=True)


@given(parsers.parse('the clinicians "{names}" work in "{zone}"'))
def clinicians_in(world: FakeWorld, outcome: Outcome, names: str, zone: str) -> None:
    for name in names.split(", "):
        add_clinician(world, outcome, name, zone, active=True)


@given("the admin is signed in")
def admin_signed_in(world: FakeWorld, outcome: Outcome) -> None:
    fake_user(world, user_id=outcome.admin, role=Role.ADMIN, name="Admin")
    fake_user(world, user_id=outcome.patient, role=Role.PATIENT, name="Patient")


@given(
    parsers.parse(
        '"{name}" has a "{status}" "{source}" appointment at "{local}" for {minutes:d} minutes'
    )
)
def appointment(
    world: FakeWorld,
    outcome: Outcome,
    name: str,
    status: str,
    source: str,
    local: str,
    minutes: int,
) -> None:
    add_appointment(world, outcome, name, datetime.fromisoformat(local), minutes, status, source)


@given(parsers.parse('"{name}" has appointments on the days "{days}" before today'))
def appointments_on_days(world: FakeWorld, outcome: Outcome, name: str, days: str) -> None:
    zone = ZoneInfo(world.activity.clinicians[outcome.clinicians[name]].time_zone)
    today = world.clock.now().astimezone(zone).date()
    for back in days.split(", "):
        local = datetime.combine(today - timedelta(days=int(back)), time(9))
        add_appointment(world, outcome, name, local, 30, "BOOKED", "ONLINE")


def rule(weekday: int, start: str, end: str) -> RuleHours:
    return RuleHours(weekday, time.fromisoformat(start), time.fromisoformat(end), VALID_FROM, None)


@given(parsers.parse('"{name}" has a rule on weekday {weekday:d} from "{start}" to "{end}"'))
def has_rule(
    world: FakeWorld, outcome: Outcome, name: str, weekday: int, start: str, end: str
) -> None:
    world.activity.clinicians[outcome.clinicians[name]].rules.append(rule(weekday, start, end))


@given(
    parsers.parse(
        'the inactive clinician "{name}" in "{zone}" has a rule on weekday {weekday:d} '
        'from "{start}" to "{end}"'
    )
)
def inactive_rule(
    world: FakeWorld, outcome: Outcome, name: str, zone: str, weekday: int, start: str, end: str
) -> None:
    clinician = add_clinician(world, outcome, name, zone, active=False)
    world.activity.clinicians[clinician].rules.append(rule(weekday, start, end))


@given(parsers.parse('"{name}" is off from "{start}" to "{end}"'))
def is_off(world: FakeWorld, outcome: Outcome, name: str, start: str, end: str) -> None:
    clinician = world.activity.clinicians[outcome.clinicians[name]]
    zone = ZoneInfo(clinician.time_zone)
    clinician.absences.append(
        Absence(
            datetime.fromisoformat(start).replace(tzinfo=zone),
            datetime.fromisoformat(end).replace(tzinfo=zone),
        )
    )


@given(parsers.parse('waitlist entries with the statuses "{statuses}"'))
def waitlist(world: FakeWorld, statuses: str) -> None:
    world.activity.waitlist.extend(statuses.split(", "))


def view(world: FakeWorld, outcome: Outcome, actor: Id, raw: str) -> None:
    try:
        outcome.dashboard = world.app.view_dashboard.execute(
            actor_id=actor, period=Range.parse(raw)
        )
    except DomainError as error:
        outcome.error = error


@when(parsers.parse('the admin views the dashboard for the range "{raw}"'))
def admin_views(world: FakeWorld, outcome: Outcome, raw: str) -> None:
    view(world, outcome, outcome.admin, raw)


@when("the admin views the dashboard without a range")
def admin_views_default(world: FakeWorld, outcome: Outcome) -> None:
    view(world, outcome, outcome.admin, "")


@when(parsers.parse('the patient views the dashboard for the range "{raw}"'))
def patient_views(world: FakeWorld, outcome: Outcome, raw: str) -> None:
    view(world, outcome, outcome.patient, raw)


@then(parsers.parse('the range is "{value}"'))
def range_is(outcome: Outcome, value: str) -> None:
    assert outcome.shown.range is Range(value)


@then(
    parsers.parse(
        "the dashboard counts {appointments:d} appointments and {cancelled:d} cancellations"
    )
)
def counts(outcome: Outcome, appointments: int, cancelled: int) -> None:
    assert (outcome.shown.appointments, outcome.shown.cancellations) == (appointments, cancelled)


@then(parsers.parse("the utilisation is {percent:d} %"))
def utilisation(outcome: Outcome, percent: int) -> None:
    assert outcome.shown.utilisation.percent == percent


@then(parsers.parse("the no-show rate is {percent:d} %"))
def no_show_rate(outcome: Outcome, percent: int) -> None:
    assert outcome.shown.no_show_rate.percent == percent


@then(parsers.parse("the online share is {percent:d} %"))
def online_share(outcome: Outcome, percent: int) -> None:
    assert outcome.shown.online_share.percent == percent


@then(parsers.parse("the waitlist size is {size:d}"))
def waitlist_size(outcome: Outcome, size: int) -> None:
    assert outcome.shown.waitlist_size == size


@then('the utilisation, no-show rate and online share are "n/a"')
def all_na(outcome: Outcome) -> None:
    d = outcome.shown
    assert (d.utilisation.percent, d.no_show_rate.percent, d.online_share.percent) == (
        None,
        None,
        None,
    )


@then("the dashboard is forbidden")
def forbidden(outcome: Outcome) -> None:
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.FORBIDDEN


@then(parsers.parse('the histogram reads "{expected}"'))
def histogram(outcome: Outcome, expected: str) -> None:
    assert ", ".join(f"{d.day:%m-%d}:{d.count}" for d in outcome.shown.per_day) == expected


@then(parsers.parse("the histogram has {days:d} days counting {total:d} appointments"))
def histogram_size(outcome: Outcome, days: int, total: int) -> None:
    per_day = outcome.shown.per_day
    assert (len(per_day), sum(d.count for d in per_day)) == (days, total)


@then(parsers.parse('the busiest clinicians read "{expected}"'))
def busiest(outcome: Outcome, expected: str) -> None:
    assert ", ".join(f"{c.name}:{c.count}" for c in outcome.shown.busiest) == expected
