from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given
from hypothesis import strategies as st

from drlibre.reporting.domain.available_minutes import Absence, RuleHours, available_minutes

ZONES = st.sampled_from(("Europe/Paris", "America/Cayenne", "Pacific/Kiritimati", "UTC"))
FIRST = date(2026, 1, 1)
START = datetime(2025, 12, 30, tzinfo=UTC)


@st.composite
def rules(draw: st.DrawFn) -> RuleHours:
    start = draw(st.integers(0, 23 * 60))
    end = draw(st.integers(start + 1, 23 * 60 + 59))
    return RuleHours(
        weekday=draw(st.integers(0, 6)),
        start=time(start // 60, start % 60),
        end=time(end // 60, end % 60),
        valid_from=FIRST,
        valid_to=None,
    )


@st.composite
def absences(draw: st.DrawFn) -> Absence:
    start = START + timedelta(minutes=draw(st.integers(0, 60 * 24 * 20)))
    return Absence(start, start + timedelta(minutes=draw(st.integers(1, 60 * 24 * 3))))


def week(first: date) -> tuple[date, ...]:
    return tuple(first + timedelta(days=n) for n in range(7))


DAYS = st.integers(0, 10).map(lambda offset: week(FIRST + timedelta(days=offset)))


@given(st.lists(rules(), max_size=4), st.lists(absences(), max_size=4), DAYS, ZONES)
def test_time_off_never_adds_minutes_nor_goes_negative(rules_, absences_, days, zone) -> None:
    """Spec 13: available minutes are rule hours minus time off."""
    tz = ZoneInfo(zone)
    without = available_minutes(rules_, (), days, tz)
    with_off = available_minutes(rules_, absences_, days, tz)
    assert 0 <= with_off <= without


@given(st.lists(rules(), max_size=4), DAYS, ZONES)
def test_time_off_covering_every_rule_leaves_no_minute(rules_, days, zone) -> None:
    """Phase 3: an absence covering the rules gives 0 minutes."""
    everything = Absence(START - timedelta(days=2), START + timedelta(days=30))
    assert available_minutes(rules_, (everything,), days, ZoneInfo(zone)) == 0


@given(st.lists(rules(), max_size=4), st.lists(absences(), max_size=4), DAYS, ZONES)
def test_time_off_outside_the_days_removes_nothing(rules_, absences_, days, zone) -> None:
    """Phase 3: outside the rules, time off removes nothing."""
    tz = ZoneInfo(zone)
    later = [Absence(a.start + timedelta(days=60), a.end + timedelta(days=60)) for a in absences_]
    assert available_minutes(rules_, later, days, tz) == available_minutes(rules_, (), days, tz)


@given(st.lists(rules(), max_size=4), DAYS, ZONES)
def test_a_week_counts_each_rule_once(rules_, days, zone) -> None:
    """Spec 13: over seven days each weekly rule gives its hours once; overlaps count once."""
    tz = ZoneInfo(zone)
    total = available_minutes(rules_, (), days, tz)
    one_by_one = sum(available_minutes((r,), (), days, tz) for r in rules_)
    assert total <= one_by_one
    for r in rules_:
        day_length = datetime.combine(FIRST, r.end) - datetime.combine(FIRST, r.start)
        assert available_minutes((r,), (), days, tz) == day_length.total_seconds() // 60


@given(st.lists(rules(), max_size=4), DAYS, ZONES)
def test_rules_outside_their_validity_give_nothing(rules_, days, zone) -> None:
    """Spec 13: only rules valid on a day count for it."""
    expired = [
        RuleHours(r.weekday, r.start, r.end, FIRST - timedelta(days=10), FIRST - timedelta(days=1))
        for r in rules_
    ]
    assert available_minutes(expired, (), days, ZoneInfo(zone)) == 0
