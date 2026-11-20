from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveSpecialty
from drlibre.organisation.application.ports.outbound import Specialties
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class SaveSpecialtyUseCase(SaveSpecialty):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, specialties: Specialties
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="specialty")
        self._specialties = specialties

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._specialties,
            build=Specialty.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
        )
