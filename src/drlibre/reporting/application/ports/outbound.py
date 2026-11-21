from datetime import datetime
from typing import Protocol

from drlibre.reporting.domain.available_minutes import ClinicianSchedule
from drlibre.reporting.domain.dashboard import BusyClinician, DayCount, Range, Tally
from drlibre.shared_kernel.ids import Id


class ActivityQueries(Protocol):
    """Appointments count in the local day of their clinician's hospital, today included."""

    def tally(self, now: datetime, period: Range) -> Tally:
        """Counts by status and source of the range; active minutes of active clinicians only."""
        ...

    def per_day(self, now: datetime, period: Range) -> tuple[DayCount, ...]:
        """Not cancelled appointments per local day of the range with any, oldest first."""
        ...

    def busiest(self, now: datetime, period: Range, limit: int) -> tuple[BusyClinician, ...]:
        """Clinicians by not cancelled appointments in the range, most first then by name."""
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
