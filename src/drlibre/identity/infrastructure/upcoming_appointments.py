from datetime import datetime

from drlibre.identity.application.ports.outbound import UpcomingAppointments
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class NoAppointmentsYet(UpcomingAppointments):
    """Null adapter until the scheduling context stores appointments."""

    def active_upcoming_for_clinician(
        self, clinician_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        return ()

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        return ()
