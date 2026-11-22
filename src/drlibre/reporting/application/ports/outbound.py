from datetime import datetime
from typing import Protocol

from drlibre.reporting.domain.available_minutes import ClinicianSchedule
from drlibre.reporting.domain.dashboard import Activity, Range
from drlibre.shared_kernel.ids import Id


class ActivityQueries(Protocol):
    """Appointments count in the local day of their clinician's hospital, today included."""

    def activity(self, now: datetime, period: Range, limit: int) -> Activity:
        """Tally, not cancelled per local day oldest first, `limit` busiest by count then name."""
        ...

    def waitlist_size(self) -> int:
        """Entries currently WAITING or OFFERED, whatever their dates."""
        ...

    def schedules(self, start: datetime, end: datetime) -> tuple[ClinicianSchedule, ...]:
        """Every active clinician's rules, and time off overlapping [start, end)."""
        ...


class Admins(Protocol):
    def is_admin(self, user_id: Id) -> bool:
        """Whether the id is an active admin."""
        ...
