from collections import defaultdict
from datetime import datetime

from drlibre.scheduling.application.ports.inbound import AvailabilityQueries, RoomUsage
from drlibre.scheduling.application.ports.outbound import (
    ActiveAppointments,
    AppointmentType,
    AvailabilityRules,
    Clinician,
    Room,
    SchedulingDirectory,
    SlotQueries,
    SlotStore,
    StoredSlot,
    TimeOffs,
)
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id

INACTIVE_STATUSES = frozenset({"CANCELLED", "NO_SHOW"})


class InMemoryAvailabilityRules(AvailabilityRules):
    def __init__(self) -> None:
        self.rows: dict[Id, AvailabilityRule] = {}

    def get(self, rule_id: Id) -> AvailabilityRule | None:
        return self.rows.get(rule_id)

    def save(self, rule: AvailabilityRule) -> None:
        self.rows[rule.id] = rule

    def delete(self, rule_id: Id) -> None:
        self.rows.pop(rule_id, None)

    def for_clinician(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        return tuple(r for r in self.rows.values() if r.clinician_id == clinician_id)


class InMemoryTimeOffs(TimeOffs):
    def __init__(self) -> None:
        self.rows: dict[Id, TimeOff] = {}

    def get(self, time_off_id: Id) -> TimeOff | None:
        return self.rows.get(time_off_id)

    def save(self, time_off: TimeOff) -> None:
        self.rows[time_off.id] = time_off

    def delete(self, time_off_id: Id) -> None:
        self.rows.pop(time_off_id, None)

    def for_clinician(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        return tuple(t for t in self.rows.values() if t.clinician_id == clinician_id)


class InMemoryActiveAppointments(ActiveAppointments):
    """Holds appointments as (clinician, period, status) rows."""

    def __init__(self) -> None:
        self.rows: list[tuple[Id, Period, str]] = []

    def for_clinician(self, clinician_id: Id, *, within: Period) -> tuple[Period, ...]:
        return tuple(
            p
            for c, p, status in self.rows
            if c == clinician_id and status not in INACTIVE_STATUSES and p.overlaps(within)
        )


class InMemorySlotStore(SlotStore, SlotQueries):
    def __init__(self) -> None:
        self.rows: list[StoredSlot] = []

    def replace(self, clinician_id: Id, slots: tuple[StoredSlot, ...]) -> None:
        self.rows = [r for r in self.rows if r.clinician_id != clinician_id] + list(slots)

    def free_slots(
        self,
        appointment_type_id: Id,
        clinician_ids: tuple[Id, ...],
        *,
        within: Period,
        not_before: datetime,
    ) -> tuple[Slot, ...]:
        by_start = {
            r.slot.start: r.slot
            for r in self.rows
            if r.appointment_type_id == appointment_type_id
            and r.clinician_id in clinician_ids
            and within.covers(r.slot.period)
            and r.slot.start >= not_before
        }
        return tuple(by_start[start] for start in sorted(by_start))


class FixedSchedulingDirectory(SchedulingDirectory):
    def __init__(self) -> None:
        self.clinicians: dict[Id, Clinician] = {}
        self.types: dict[Id, AppointmentType] = {}
        self.rooms: dict[Id, Room] = {}
        self.profile_of_user: dict[Id, Id] = {}

    def clinician(self, clinician_id: Id) -> Clinician | None:
        return self.clinicians.get(clinician_id)

    def clinician_of(self, user_id: Id) -> Clinician | None:
        profile_id = self.profile_of_user.get(user_id)
        return self.clinicians.get(profile_id) if profile_id else None

    def active_clinicians(self, department_id: Id) -> tuple[Id, ...]:
        return tuple(
            c.id for c in self.clinicians.values() if c.department_id == department_id and c.active
        )

    def appointment_type(self, appointment_type_id: Id) -> AppointmentType | None:
        return self.types.get(appointment_type_id)

    def appointment_types(self, department_id: Id) -> tuple[AppointmentType, ...]:
        return tuple(t for t in self.types.values() if t.department_id == department_id)

    def room(self, room_id: Id) -> Room | None:
        return self.rooms.get(room_id)


def _weekly(rule: AvailabilityRule) -> tuple[int, object, object]:
    return rule.weekday, rule.start, rule.end


class InMemoryAvailabilityQueries(AvailabilityQueries, RoomUsage):
    """Reads straight from the in-memory rules and time off."""

    def __init__(self, *, rules: InMemoryAvailabilityRules, time_offs: InMemoryTimeOffs) -> None:
        self.rules = rules
        self.time_offs = time_offs

    def rules_of(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        return tuple(sorted(self.rules.for_clinician(clinician_id), key=_weekly))

    def time_offs_of(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        found = self.time_offs.for_clinician(clinician_id)
        return tuple(sorted(found, key=lambda t: (t.start, t.end)))

    def weekly_summary(
        self, clinician_ids: frozenset[Id]
    ) -> dict[Id, tuple[AvailabilityRule, ...]]:
        grouped: defaultdict[Id, list[AvailabilityRule]] = defaultdict(list)
        for rule in sorted(self.rules.rows.values(), key=_weekly):
            if rule.clinician_id in clinician_ids:
                grouped[rule.clinician_id].append(rule)
        return {clinician: tuple(rules) for clinician, rules in grouped.items()}

    def rules_using(self, room_id: Id) -> tuple[Dependent, ...]:
        used = sorted((r for r in self.rules.rows.values() if r.room_id == room_id), key=_weekly)
        return tuple(Dependent("availability_rule", r.id, r.label) for r in used)
