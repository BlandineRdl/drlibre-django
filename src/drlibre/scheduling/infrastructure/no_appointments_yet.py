from drlibre.scheduling.application.ports.outbound import ActiveAppointments
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class NoAppointmentsYet(ActiveAppointments):
    """Null adapter until booking (E3) models appointments."""

    def for_clinician(self, clinician_id: Id, *, within: Period) -> tuple[Period, ...]:
        return ()
