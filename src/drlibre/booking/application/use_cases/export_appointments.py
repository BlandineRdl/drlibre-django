from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    ExportAppointments,
    ExportRow,
)
from drlibre.booking.application.ports.outbound import AdminAppointments, Staff
from drlibre.booking.application.use_cases.admin_only import refuse_non_admin
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class ExportAppointmentsUseCase(ExportAppointments):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        staff: Staff,
        appointments: AdminAppointments,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._staff = staff
        self._appointments = appointments

    def execute(
        self, *, actor_id: Id, appointment_filter: AdminAppointmentFilter
    ) -> tuple[ExportRow, ...]:
        refuse_non_admin(self._staff, actor_id)
        with self._uow:
            rows = self._appointments.all(appointment_filter)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor_id,
                    action="booking.appointments_exported",
                    entity_type="appointment",
                    entity_id=None,
                    at=self._clock.now(),
                    metadata={"count": len(rows)},
                )
            )
            return rows
