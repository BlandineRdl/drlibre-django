from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import DeleteHospital
from drlibre.organisation.application.ports.outbound import Departments, Hospitals
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.hospital import Hospital
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependent, Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteHospitalUseCase(DeleteHospital):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        hospitals: Hospitals,
        departments: Departments,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="hospital")
        self._hospitals = hospitals
        self._departments = departments

    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        self._writes.delete(
            records=self._hospitals,
            actor=actor,
            record_id=record_id,
            dependents=self._dependents,
            message="Cet hôpital a encore des départements.",
        )

    def _dependents(self, hospital: Hospital) -> Dependents:
        departments = self._departments.for_hospital(hospital.id)
        return Dependents(tuple(Dependent("department", d.id, d.label) for d in departments))
