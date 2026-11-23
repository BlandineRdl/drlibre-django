from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from drlibre.scheduling.domain.availability_rule import WEEKDAYS, AvailabilityRule
from drlibre.scheduling.domain.slot import Slot, SlotState, SlotStatus
from drlibre.scheduling.domain.time_off import MAX_REASON as MAX_TIME_OFF_REASON
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id

__all__ = [
    "MAX_TIME_OFF_REASON",
    "WEEKDAYS",
    "AvailabilityQueries",
    "AvailabilityRule",
    "DeleteAvailabilityRule",
    "DeleteTimeOff",
    "ExtendSlotHorizon",
    "FindFreeSlots",
    "FindFreeWeek",
    "FindSlotStates",
    "FreeCliniciansAt",
    "FreeWeek",
    "IsSlotFree",
    "NextBookableSlots",
    "ReadSlotState",
    "RecordTimeOff",
    "RefreshSlots",
    "RoomUsage",
    "SaveAvailabilityRule",
    "Slot",
    "SlotState",
    "SlotStatus",
    "TimeOff",
]


class FindFreeSlots(Protocol):
    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        end: datetime,
        ignoring_appointment: Id | None = None,
    ) -> tuple[Slot, ...]:
        """Sorted free slots, the ignored appointment's time freed; invalid_input over 31 days."""
        ...


FREE_ONLY = frozenset({SlotStatus.FREE})


class FindSlotStates(Protocol):
    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        end: datetime,
        statuses: frozenset[SlotStatus] = FREE_ONLY,
        staff: bool = False,
    ) -> tuple[SlotState, ...]:
        """FindFreeSlots per clinician with its rule, by start; other statuses staff only."""
        ...


class ReadSlotState(Protocol):
    def execute(
        self, *, appointment_type_id: Id, clinician_id: Id, start: datetime, staff: bool = False
    ) -> SlotState | None:
        """The clinician's slot starting there, any status for staff, else free only, or None."""
        ...


@dataclass(frozen=True, slots=True)
class FreeWeek:
    """One Monday-to-Sunday week of free slots, its neighbours None outside the horizon."""

    monday: date
    previous_monday: date | None
    next_monday: date | None
    time_zone: str
    slots: tuple[Slot, ...]


class FindFreeWeek(Protocol):
    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id,
        week: date | None,
        ignoring_appointment: Id | None = None,
        for_patient: bool = True,
    ) -> FreeWeek:
        """Free slots of the asked or current week, lead time for patients; not_found if no type."""
        ...


class NextBookableSlots(Protocol):
    def execute(self, *, appointment_type_id: Id, clinician_id: Id | None) -> tuple[Slot, ...]:
        """Sorted bookable slots; empty if type or clinician is unknown, None is the department."""
        ...


class IsSlotFree(Protocol):
    def execute(
        self,
        *,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        ignoring_hold: Id | None,
        ignoring_appointment: Id | None = None,
    ) -> bool:
        """Whether the start is a free, unheld slot of the active clinician, appointment ignored."""
        ...


class FreeCliniciansAt(Protocol):
    def execute(self, *, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        """Active clinicians of the type's department with a free slot at the start."""
        ...


class RefreshSlots(Protocol):
    def execute(self, *, clinician_id: Id) -> None:
        """Rebuild the clinician's stored slots from today to the horizon, in the caller's unit."""
        ...


class ExtendSlotHorizon(Protocol):
    def execute(self) -> None:
        """Rebuild every clinician's stored slots from today to the horizon, one unit each."""
        ...


class SaveAvailabilityRule(Protocol):
    def execute(self, *, actor: Id, rule_id: Id | None, fields: Mapping[str, str]) -> Id:
        """Create (no id) or edit the caller's own rule; invalid_input, forbidden or not_found."""
        ...


class DeleteAvailabilityRule(Protocol):
    def execute(self, *, actor: Id, rule_id: Id) -> None:
        """Delete the caller's own rule; forbidden for another's, not_found when absent."""
        ...


class RecordTimeOff(Protocol):
    def execute(self, *, actor: Id, fields: Mapping[str, str]) -> Id:
        """Record the caller's time off in local time; invalid_input, identical period included."""
        ...


class DeleteTimeOff(Protocol):
    def execute(self, *, actor: Id, time_off_id: Id) -> None:
        """Delete the caller's own time off; forbidden for another's, not_found when absent."""
        ...


class AvailabilityQueries(Protocol):
    def rule(self, rule_id: Id) -> AvailabilityRule | None:
        """The rule whoever owns it, or None when unknown."""
        ...

    def time_off(self, time_off_id: Id) -> TimeOff | None:
        """The time off whoever owns it, or None when unknown."""
        ...

    def rules_of(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        """The clinician's rules by weekday then start; empty when there are none."""
        ...

    def time_offs_of(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        """The clinician's time off by start; empty when there is none."""
        ...

    def weekly_summary(
        self, clinician_ids: frozenset[Id]
    ) -> dict[Id, tuple[AvailabilityRule, ...]]:
        """Rules of each named clinician by weekday then start; clinicians without rules absent."""
        ...


class RoomUsage(Protocol):
    def rules_using(self, room_id: Id) -> tuple[Dependent, ...]:
        """Availability rules naming the room, labelled by weekday and hours, never a person."""
        ...
