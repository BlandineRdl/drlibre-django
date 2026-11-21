from datetime import datetime

from drlibre.booking.application.ports.inbound import AppointmentQueries
from drlibre.identity.application.ports.outbound import UpcomingAppointments
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class BookingUpcomingAppointments(UpcomingAppointments):
    """Asks booking, through its inbound port, which appointments a user still has."""

    def __init__(self, queries: AppointmentQueries) -> None:
        self._queries = queries

    def active_upcoming_for_clinician(
        self, clinician_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        return self._queries.active_upcoming_for_clinician_user(clinician_id, after=after)

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        return self._queries.any_for_user(user_id)
