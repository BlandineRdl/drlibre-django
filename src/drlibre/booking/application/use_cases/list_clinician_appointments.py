from drlibre.booking.application.ports.inbound import (
    ClinicianEntry,
    ClinicianFilter,
    ListClinicianAppointments,
)
from drlibre.booking.application.ports.outbound import BookingDirectory, ClinicianAgenda
from drlibre.booking.application.use_cases.clinician_read_helpers import with_actions
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.shared_kernel.ids import Id


class ListClinicianAppointmentsUseCase(ListClinicianAppointments):
    def __init__(self, *, directory: BookingDirectory, agenda: ClinicianAgenda) -> None:
        self._directory = directory
        self._agenda = agenda

    def execute(
        self, *, actor_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        profile_id = clinician_profile(self._directory, actor_id)
        return tuple(with_actions(e) for e in self._agenda.entries(profile_id, agenda_filter))
