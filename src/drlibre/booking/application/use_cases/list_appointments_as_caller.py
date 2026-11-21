from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    AgendaFilter,
    AppointmentsQuery,
    ClinicianAppointments,
    ClinicianFilter,
    ListAllAppointments,
    ListAppointmentsAsCaller,
    ListClinicianAppointments,
    ListPatientAppointments,
    PatientAppointments,
)
from drlibre.booking.application.ports.outbound import BookingDirectory, Staff
from drlibre.booking.application.use_cases.actor_scope import ActorKind, actor_scope
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


class ListAppointmentsAsCallerUseCase(ListAppointmentsAsCaller):
    def __init__(
        self,
        *,
        directory: BookingDirectory,
        staff: Staff,
        list_clinician_appointments: ListClinicianAppointments,
        list_patient_appointments: ListPatientAppointments,
        list_all_appointments: ListAllAppointments,
    ) -> None:
        self._directory = directory
        self._staff = staff
        self._list_all_appointments = list_all_appointments
        self._list_clinician_appointments = list_clinician_appointments
        self._list_patient_appointments = list_patient_appointments

    def execute(
        self, *, actor_id: Id, query: AppointmentsQuery
    ) -> PatientAppointments | ClinicianAppointments | Page[AdminAppointmentRow]:
        kind = actor_scope(self._directory, self._staff, actor_id).kind
        if kind is ActorKind.CLINICIAN:
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
        if kind is ActorKind.ADMIN:
            return self._list_all_appointments.execute(
                actor_id=actor_id,
                appointment_filter=AdminAppointmentFilter(
                    start_date=query.start.date() if query.start else None,
                    end_date=query.end.date() if query.end else None,
                    department_id=query.department_id,
                    clinician_id=query.clinician_id,
                    status=query.status,
                    source=query.source,
                ),
                request=PageRequest(number=query.page),
            )
        return self._list_patient_appointments.execute(
            patient_id=actor_id,
            agenda_filter=AgendaFilter(
                clinician_id=query.clinician_id,
                status=query.status,
                start=query.start,
                end=query.end,
            ),
        )
