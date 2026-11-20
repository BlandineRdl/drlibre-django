from datetime import datetime

from drlibre.identity.application.ports.outbound import UpcomingAppointments
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class InMemoryUpcomingAppointments(UpcomingAppointments):
    """Holds appointments as (clinician, patient, start, active, dependent) rows."""

    def __init__(self) -> None:
        self.rows: list[tuple[Id, Id, datetime, bool, Dependent]] = []

    def active_upcoming_for_clinician(
        self, clinician_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        return tuple(
            d
            for c, _, start, active, d in self.rows
            if c == clinician_id and active and start > after
        )

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        return tuple(d for c, p, _, _, d in self.rows if user_id in {c, p})
