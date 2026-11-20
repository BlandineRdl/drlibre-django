from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveHospital
from drlibre.organisation.application.ports.outbound import Hospitals
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.hospital import Hospital
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class SaveHospitalUseCase(SaveHospital):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, hospitals: Hospitals
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="hospital")
        self._hospitals = hospitals

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._hospitals,
            build=Hospital.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
        )
