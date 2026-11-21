from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    ListAllAppointments,
)
from drlibre.booking.application.ports.outbound import AdminAppointments, Staff
from drlibre.booking.application.use_cases.admin_only import refuse_non_admin
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


class ListAllAppointmentsUseCase(ListAllAppointments):
    def __init__(self, *, staff: Staff, appointments: AdminAppointments) -> None:
        self._staff = staff
        self._appointments = appointments

    def execute(
        self, *, actor_id: Id, appointment_filter: AdminAppointmentFilter, request: PageRequest
    ) -> Page[AdminAppointmentRow]:
        refuse_non_admin(self._staff, actor_id)
        return self._appointments.page(appointment_filter, request)
