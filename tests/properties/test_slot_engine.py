"""Behaviour properties of the spec 5.1 free-slot engine."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given
from hypothesis import strategies as st

from drlibre.scheduling.application.ports.outbound import AppointmentType, Clinician
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation
from drlibre.scheduling.application.use_cases.find_free_slots import FindFreeSlotsUseCase
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.domain.appointment import Appointment
from drlibre.scheduling.domain.availability_rule import AvailabilityRule, weekday_of
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.domain.slot_engine import SlotEngine
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import appointment, rule, time_off
from tests.fakes.clock import FixedClock
from tests.fakes.scheduling import (
    FixedSchedulingDirectory,
    InMemoryAvailabilityRules,
    InMemoryClinicianAppointments,
    InMemoryRoomBookings,
    InMemorySlotHolds,
    InMemorySlotStore,
    InMemoryTimeOffs,
)

PARIS = ZoneInfo("Europe/Paris")
CLINICIAN = Id()
DST_DAYS = [date(2026, 3, 29) + timedelta(days=d) for d in range(-3, 4)] + [
    date(2026, 10, 25) + timedelta(days=d) for d in range(-3, 4)
]

days = st.sampled_from(DST_DAYS) | st.dates(date(2026, 1, 1), date(2027, 12, 31))
starts = st.integers(0, 20 * 12).map(lambda n: time(n // 12, n % 12 * 5))
minutes = st.integers(5, 240)


def day_window(day: date, tz: ZoneInfo = PARIS) -> Period:
    start = datetime.combine(day, time(), tzinfo=tz)
    return Period(start, datetime.combine(day + timedelta(days=1), time(), tzinfo=tz))


def engine(
    rules: Sequence[AvailabilityRule],
    *,
    duration: int = 30,
    buffer: int = 0,
    off: Sequence[TimeOff] = (),
    busy: Sequence[Period] = (),
) -> SlotEngine:
    return SlotEngine(
        rules=rules,
        time_off=off,
        busy=busy,
        duration=timedelta(minutes=duration),
        buffer=timedelta(minutes=buffer),
        time_zone=PARIS,
    )


@given(day=st.sampled_from(DST_DAYS))
def test_a_morning_rule_starts_at_nine_local_on_daylight_saving_weeks(day: date) -> None:
    morning = rule(CLINICIAN, weekday=weekday_of(day), start=time(9), end=time(12))
    slots = engine([morning]).free_slots(day_window(day))
    local = [s.start.astimezone(PARIS).strftime("%H:%M") for s in slots]
    assert local == [f"{9 + q // 4:02d}:{q % 4 * 15:02d}" for q in range(11)]


@given(day=days, start=starts, length=minutes, step=minutes, duration=st.integers(1, 120))
def test_slots_follow_the_rule_step_and_fit_inside_it(
    day: date, start: time, length: int, step: int, duration: int
) -> None:
    opening = datetime.combine(day, start, tzinfo=PARIS)
    end = (opening + timedelta(minutes=length)).time()
    if end <= start:
        return
    window = rule(CLINICIAN, weekday=weekday_of(day), start=start, end=end, step_minutes=step)
    slots = engine([window], duration=duration).free_slots(day_window(day))
    first = opening.astimezone(UTC)
    last = datetime.combine(day, end, tzinfo=PARIS).astimezone(UTC)
    for slot in slots:
        assert slot.start.tzinfo is UTC
        assert slot.end - slot.start == timedelta(minutes=duration)
        assert (slot.start - first) % timedelta(minutes=step) == timedelta()
        assert first <= slot.start
        assert slot.end <= last


@given(
    day=days,
    first=starts,
    second=starts,
    step=st.integers(5, 60),
    span=st.tuples(st.integers(-600, 1200), st.integers(1, 600)),
)
def test_starts_are_unique_sorted_and_inside_the_range(
    day: date, first: time, second: time, step: int, span: tuple[int, int]
) -> None:
    rules = [
        rule(CLINICIAN, weekday=weekday_of(day), start=s, end=time(22), step_minutes=step)
        for s in (first, second)
    ]
    origin = datetime.combine(day, time(), tzinfo=PARIS)
    within = Period(origin + timedelta(minutes=span[0]), origin + timedelta(minutes=sum(span)))
    slots = engine(rules).free_slots(within)
    starts_ = [s.start for s in slots]
    assert starts_ == sorted(set(starts_))
    assert all(within.covers(s.period) for s in slots)


@given(
    day=days,
    at=st.integers(0, 47),
    length=st.integers(1, 180),
    buffer=st.integers(0, 60),
    blocked_by=st.sampled_from(["time off", "appointment"]),
)
def test_no_slot_overlaps_time_off_or_a_buffered_appointment(
    day: date, at: int, length: int, buffer: int, blocked_by: str
) -> None:
    midnight = datetime.combine(day, time(), tzinfo=PARIS).astimezone(UTC)
    busy_start = midnight + timedelta(minutes=at * 30)
    busy = Period(busy_start, busy_start + timedelta(minutes=length))
    all_day = rule(
        CLINICIAN, weekday=weekday_of(day), start=time(0), end=time(23, 55), step_minutes=5
    )
    if blocked_by == "time off":
        built = engine([all_day], off=[time_off(CLINICIAN, busy.start, busy.end)])
        blocked = busy
    else:
        built = engine([all_day], buffer=buffer, busy=[busy])
        blocked = busy.extended(timedelta(minutes=buffer))
    slots = built.free_slots(day_window(day))
    assert not any(s.period.overlaps(blocked) for s in slots)
    free_after = blocked.end.astimezone(PARIS)
    if (
        free_after.date() == day
        and free_after.time() <= time(23, 25)
        and free_after.minute % 5 == 0
    ):
        assert blocked.end in {s.start for s in slots}


@dataclass(frozen=True)
class Setting:
    now: datetime
    day: date
    department: Id
    kind: AppointmentType
    rule: AvailabilityRule


def _free_slots(
    appointments: Sequence[tuple[Id, Appointment]], *, ignoring: Id | None, setting: Setting
) -> tuple[Slot, ...]:
    directory = FixedSchedulingDirectory()
    clinician = Clinician(CLINICIAN, setting.department, "Europe/Paris", active=True)
    directory.clinicians[CLINICIAN] = clinician
    directory.types[setting.kind.id] = setting.kind
    rules, offs = InMemoryAvailabilityRules(), InMemoryTimeOffs()
    rules.rows[setting.rule.id] = setting.rule
    booked = InMemoryClinicianAppointments()
    booked.rows.extend(appointments)
    store, holds, clock = InMemorySlotStore(), InMemorySlotHolds(), FixedClock(setting.now)
    RefreshSlotsUseCase(
        clock=clock,
        directory=directory,
        rules=rules,
        time_offs=offs,
        appointments=booked,
        store=store,
    ).execute(clinician_id=CLINICIAN)
    computation = SlotComputation(
        directory=directory, rules=rules, time_offs=offs, appointments=booked
    )
    window = day_window(setting.day)
    return FindFreeSlotsUseCase(
        clock=clock,
        directory=directory,
        queries=store,
        holds=holds,
        rooms=InMemoryRoomBookings(),
        computation=computation,
    ).execute(
        appointment_type_id=setting.kind.id,
        clinician_id=CLINICIAN,
        start=window.start,
        end=window.end,
        ignoring_appointment=ignoring,
    )


@given(
    offset=st.integers(0, 10),
    hour=st.integers(0, 23),
    step=st.sampled_from([10, 15, 30]),
    duration=st.integers(10, 60),
    buffer=st.integers(0, 30),
    booked=st.lists(
        st.tuples(st.integers(0, 60), st.integers(1, 12), st.booleans()), min_size=1, max_size=4
    ),
)
def test_ignoring_an_appointment_frees_what_a_refresh_without_it_would_store(
    offset: int,
    hour: int,
    step: int,
    duration: int,
    buffer: int,
    booked: list[tuple[int, int, bool]],
) -> None:
    """Story déplacement : le RDV déplacé est ignoré, son heure redevient un créneau libre."""
    now = datetime(2026, 11, 20, hour, tzinfo=UTC)
    day = now.astimezone(PARIS).date() + timedelta(days=offset)
    department = Id()
    kind = AppointmentType(
        Id(), department, duration, buffer, active=True, time_zone="Europe/Paris"
    )
    morning = rule(
        CLINICIAN, weekday=weekday_of(day), start=time(8), end=time(18), step_minutes=step
    )
    origin = datetime.combine(day, time(7, 30), tzinfo=PARIS)
    appointments = [
        appointment(
            CLINICIAN,
            origin + timedelta(minutes=10 * at),
            origin + timedelta(minutes=10 * (at + length)),
            status="BOOKED" if active else "CANCELLED",
        )
        for at, length, active in booked
    ]
    setting = Setting(now, day, department, kind, morning)
    ignored = appointments[0][1].id

    ignoring = _free_slots(appointments, ignoring=ignored, setting=setting)
    without = _free_slots(appointments[1:], ignoring=None, setting=setting)

    assert ignoring == without
