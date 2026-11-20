from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import DeleteAppointmentType
from drlibre.organisation.application.ports.outbound import AppointmentTypes, ScheduleDependents
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteAppointmentTypeUseCase(DeleteAppointmentType):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        appointment_types: AppointmentTypes,
        schedule: ScheduleDependents,
    ) -> None:
        self._writes = RecordWrites(
            clock=clock, uow=uow, audit=audit, entity_type="appointment_type"
        )
        self._appointment_types = appointment_types
        self._schedule = schedule

    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        self._writes.delete(
            records=self._appointment_types,
            actor=actor,
            record_id=record_id,
            dependents=self._dependents,
            message="Ce type de RDV a encore des rendez-vous ou une liste d'attente.",
        )

    def _dependents(self, appointment_type: AppointmentType) -> Dependents:
        return Dependents(self._schedule.for_appointment_type(appointment_type.id))
