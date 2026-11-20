from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Slot
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id

__all__ = [
    "AvailabilityQueries",
    "AvailabilityRule",
    "DeleteAvailabilityRule",
    "DeleteTimeOff",
    "ExtendSlotHorizon",
    "FindFreeSlots",
    "RecordTimeOff",
    "RefreshSlots",
    "RoomUsage",
    "SaveAvailabilityRule",
    "Slot",
    "TimeOff",
]


class FindFreeSlots(Protocol):
    def execute(
        self, *, appointment_type_id: Id, clinician_id: Id | None, start: datetime, end: datetime
    ) -> tuple[Slot, ...]:
        """Sorted free slots; invalid_input over 31 days, not_found for a bad type or clinician."""
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
