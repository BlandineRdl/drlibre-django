from drlibre.booking.application.ports.inbound import AppointmentQueries
from drlibre.scheduling.application.ports.outbound import ClinicianAppointments
from drlibre.scheduling.domain.appointment import Appointment, AppointmentStatus
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class BookingClinicianAppointments(ClinicianAppointments):
    """Reads the clinician's appointments through booking's inbound port."""

    def __init__(self, queries: AppointmentQueries) -> None:
        self._queries = queries

    def for_clinician(self, clinician_id: Id, *, within: Period) -> tuple[Appointment, ...]:
        booked = self._queries.periods_of(clinician_id, start=within.start, end=within.end)
        return tuple(
            Appointment(Period(b.start, b.end), AppointmentStatus(b.status.value)) for b in booked
        )
