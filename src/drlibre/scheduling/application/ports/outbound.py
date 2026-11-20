from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.ids import Id


class AvailabilityRules(Protocol):
    def get(self, rule_id: Id) -> AvailabilityRule | None:
        """Return the rule, or None when unknown."""
        ...

    def save(self, rule: AvailabilityRule) -> None:
        """Insert or replace the rule by id."""
        ...

    def delete(self, rule_id: Id) -> None:
        """Remove the rule; absent ids are ignored."""
        ...

    def clinicians(self) -> tuple[Id, ...]:
        """Return the ids of every clinician holding at least one rule."""
        ...

    def for_clinician(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        """Return every rule of the clinician, whatever its validity dates."""
        ...


class TimeOffs(Protocol):
    def get(self, time_off_id: Id) -> TimeOff | None:
        """Return the time off, or None when unknown."""
        ...

    def save(self, time_off: TimeOff) -> None:
        """Insert or replace the time off by id."""
        ...

    def delete(self, time_off_id: Id) -> None:
        """Remove the time off; absent ids are ignored."""
        ...

    def for_clinician(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        """Return every time off of the clinician."""
        ...


class ActiveAppointments(Protocol):
    def for_clinician(self, clinician_id: Id, *, within: Period) -> tuple[Period, ...]:
        """Return the periods of the clinician's active appointments overlapping the range."""
        ...


@dataclass(frozen=True, slots=True)
class StoredSlot:
    clinician_id: Id
    appointment_type_id: Id
    slot: Slot


class SlotStore(Protocol):
    def replace(self, clinician_id: Id, slots: tuple[StoredSlot, ...]) -> None:
        """Replace every stored slot of the clinician by the given ones."""
        ...


class SlotQueries(Protocol):
    def free_slots(
        self,
        appointment_type_id: Id,
        clinician_ids: tuple[Id, ...],
        *,
        within: Period,
        not_before: datetime,
    ) -> tuple[Slot, ...]:
        """Return stored slots inside the range starting from not_before, one per start."""
        ...


@dataclass(frozen=True, slots=True)
class Clinician:
    id: Id
    department_id: Id
    time_zone: str
    active: bool


@dataclass(frozen=True, slots=True)
class AppointmentType:
    id: Id
    department_id: Id
    duration_minutes: int
    buffer_minutes: int
    active: bool


@dataclass(frozen=True, slots=True)
class Room:
    id: Id
    department_id: Id
    active: bool


class SchedulingDirectory(Protocol):
    def clinician(self, clinician_id: Id) -> Clinician | None:
        """Return the clinician profile with its hospital time zone, or None when unknown."""
        ...

    def clinician_of(self, user_id: Id) -> Clinician | None:
        """Return the clinician profile of the user, or None when the user has none."""
        ...

    def active_clinicians(self, department_id: Id) -> tuple[Id, ...]:
        """Return the ids of the department's active clinicians."""
        ...

    def appointment_type(self, appointment_type_id: Id) -> AppointmentType | None:
        """Return the appointment type, or None when unknown."""
        ...

    def appointment_types(self, department_id: Id) -> tuple[AppointmentType, ...]:
        """Return every appointment type of the department, active or not."""
        ...

    def room(self, room_id: Id) -> Room | None:
        """Return the room, active or not, or None when unknown."""
        ...
