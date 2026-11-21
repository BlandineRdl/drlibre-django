from drlibre.booking.application.ports.inbound import (
    AgendaFilter,
    AppointmentsQuery,
    ClinicianAppointments,
    ClinicianFilter,
    ListAppointmentsAsCaller,
    ListClinicianAppointments,
    ListPatientAppointments,
    PatientAppointments,
)
from drlibre.booking.application.ports.outbound import BookingDirectory
from drlibre.shared_kernel.ids import Id


class ListAppointmentsAsCallerUseCase(ListAppointmentsAsCaller):
    def __init__(
        self,
        *,
        directory: BookingDirectory,
        list_clinician_appointments: ListClinicianAppointments,
        list_patient_appointments: ListPatientAppointments,
    ) -> None:
        self._directory = directory
        self._list_clinician_appointments = list_clinician_appointments
        self._list_patient_appointments = list_patient_appointments

    def execute(
        self, *, actor_id: Id, query: AppointmentsQuery
    ) -> PatientAppointments | ClinicianAppointments:
        if self._directory.clinician_of_user(actor_id) is not None:
            entries = self._list_clinician_appointments.execute(
                actor_id=actor_id,
                agenda_filter=ClinicianFilter(
                    patient_id=query.patient_id,
                    status=query.status,
                    start=query.start,
                    end=query.end,
                ),
            )
            return ClinicianAppointments(entries=entries)
        return self._list_patient_appointments.execute(
            patient_id=actor_id,
            agenda_filter=AgendaFilter(
                clinician_id=query.clinician_id,
                status=query.status,
                start=query.start,
                end=query.end,
            ),
        )
