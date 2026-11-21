from drlibre.booking.application.ports.inbound import ClinicianPatient, ClinicianPatients
from drlibre.booking.application.ports.outbound import BookingDirectory, ClinicianAgenda
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


class ClinicianPatientsUseCase(ClinicianPatients):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, request: PageRequest) -> Page[ClinicianPatient]:
        profile_id = clinician_profile(self._directory, actor_id)
        return self._agenda.patients(profile_id, request, self._clock.now())
