from drlibre.scheduling.application.ports.outbound import ClinicianAppointments
from drlibre.scheduling.domain.appointment import Appointment
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class NoAppointmentsYet(ClinicianAppointments):
    """Null adapter until booking (E3) models appointments."""

    def for_clinician(self, clinician_id: Id, *, within: Period) -> tuple[Appointment, ...]:
        return ()
