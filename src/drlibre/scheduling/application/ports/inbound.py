from datetime import datetime
from typing import Protocol

from drlibre.scheduling.domain.slot import Slot
from drlibre.shared_kernel.ids import Id

__all__ = ["FindFreeSlots", "RefreshSlots", "Slot"]


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
