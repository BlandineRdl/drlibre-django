"""Behaviour properties of the §15.2 slot states against the spec 5.1 free slots."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given
from hypothesis import strategies as st

from drlibre.scheduling.application.ports.outbound import AppointmentType, Clinician
from drlibre.scheduling.domain.availability_rule import weekday_of
from drlibre.scheduling.domain.slot import Period, SlotStatus
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import appointment, rule, time_off
from tests.fakes.world import FakeWorld

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)

# One taken period: what takes it, its start in 15-minute steps after 08:00 and its length.
takes = st.tuples(
    st.sampled_from(["appointment", "cancelled", "hold", "off"]),
    st.integers(0, 40),
    st.integers(1, 8),
)


@dataclass
class Department:
    world: FakeWorld = field(default_factory=FakeWorld)
    department: Id = field(default_factory=Id)
    kind: Id = field(default_factory=Id)
    clinicians: tuple[Id, ...] = ()


def a_department(
    day_offset: int, duration: int, buffer: int, step: int, taken: list[list[tuple[str, int, int]]]
) -> tuple[Department, Period]:
    scene = Department()
    world = scene.world
    day = NOW.astimezone(PARIS).date() + timedelta(days=day_offset)
    world.scheduling_directory.types[scene.kind] = AppointmentType(
        scene.kind, scene.department, duration, buffer, active=True, time_zone="Europe/Paris"
    )
    origin = datetime.combine(day, time(8), tzinfo=PARIS)
    for periods in taken:
        clinician = Id()
        scene.clinicians += (clinician,)
        world.scheduling_directory.clinicians[clinician] = Clinician(
            clinician, scene.department, "Europe/Paris", active=True
        )
        world.availability_rules.save(
            rule(clinician, weekday=weekday_of(day), start=time(8), end=time(18), step_minutes=step)
        )
        for what, at, length in periods:
            start = origin + timedelta(minutes=15 * at)
            end = start + timedelta(minutes=15 * length)
            if what == "hold":
                world.slot_holds.rows.append(
                    (Id(), clinician, Period(start, end), NOW + timedelta(minutes=10))
                )
            elif what == "off":
                world.time_offs.save(time_off(clinician, start, end))
            else:
                status = "BOOKED" if what == "appointment" else "CANCELLED"
                world.clinician_appointments.rows.append(
                    appointment(clinician, start, end, status=status)
                )
        world.app.extend_slot_horizon.execute()
    whole_day = Period(
        datetime.combine(day, time(), tzinfo=PARIS),
        datetime.combine(day + timedelta(days=1), time(), tzinfo=PARIS),
    )
    return scene, whole_day


settings = {
    "day_offset": st.integers(0, 3),
    "duration": st.sampled_from([15, 30, 45]),
    "buffer": st.sampled_from([0, 10]),
    "step": st.sampled_from([15, 30]),
    "taken": st.lists(st.lists(takes, max_size=4), min_size=1, max_size=3),
}


@given(**settings)
def test_the_free_states_are_the_free_slots_of_the_same_read(
    day_offset: int, duration: int, buffer: int, step: int, taken: list[list[tuple[str, int, int]]]
) -> None:
    """Règle §15.2 : un `Slot` libre est un créneau libre de §5.1, praticien ou département."""
    scene, day = a_department(day_offset, duration, buffer, step, taken)
    app = scene.world.app
    for clinician in (None, *scene.clinicians):
        asked = {
            "appointment_type_id": scene.kind,
            "clinician_id": clinician,
            "start": day.start,
            "end": day.end,
        }
        free = app.find_free_slots.execute(**asked)
        states = app.find_slot_states.execute(**asked)
        assert {s.start for s in states} == {s.start for s in free}
        assert all(s.status is SlotStatus.FREE for s in states)


@given(**settings)
def test_staff_see_each_start_of_a_rule_once_free_or_taken(
    day_offset: int, duration: int, buffer: int, step: int, taken: list[list[tuple[str, int, int]]]
) -> None:
    """Règle §15.2 : le personnel voit chaque début de plage une fois, libre ou pris."""
    scene, day = a_department(day_offset, duration, buffer, step, taken)
    app = scene.world.app
    asked = {
        "appointment_type_id": scene.kind,
        "clinician_id": None,
        "start": day.start,
        "end": day.end,
    }
    free = app.find_slot_states.execute(**asked)
    every = app.find_slot_states.execute(**asked, statuses=frozenset(SlotStatus), staff=True)
    keys = [(s.clinician_id, s.start) for s in every]
    assert len(keys) == len(set(keys))
    assert [s for s in every if s.status is SlotStatus.FREE] == list(free)
    assert all(s.start >= NOW for s in every)
