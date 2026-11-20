from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveDepartment
from drlibre.organisation.application.ports.outbound import Departments, Hospitals
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.department import Department
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class SaveDepartmentUseCase(SaveDepartment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        departments: Departments,
        hospitals: Hospitals,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="department")
        self._departments = departments
        self._hospitals = hospitals

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._departments,
            build=Department.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
            check=self._check,
        )

    def _check(self, before: Department | None, after: Department) -> None:
        if self._hospitals.get(after.hospital_id) is None:
            raise invalid_field("hospital_id", "Choisissez un hôpital.")
