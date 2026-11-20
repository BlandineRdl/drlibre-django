from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveAppointmentType
from drlibre.organisation.application.ports.outbound import AppointmentTypes, Departments
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class SaveAppointmentTypeUseCase(SaveAppointmentType):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        appointment_types: AppointmentTypes,
        departments: Departments,
    ) -> None:
        self._writes = RecordWrites(
            clock=clock, uow=uow, audit=audit, entity_type="appointment_type"
        )
        self._appointment_types = appointment_types
        self._departments = departments

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._appointment_types,
            build=AppointmentType.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
            check=self._check,
        )

    def _check(self, before: AppointmentType | None, after: AppointmentType) -> None:
        if self._departments.get(after.department_id) is None:
            raise invalid_field("department_id", "Choisissez un département.")
