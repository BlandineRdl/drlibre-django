from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import DeleteSpecialty
from drlibre.organisation.application.ports.outbound import ClinicianProfiles, Specialties
from drlibre.organisation.application.use_cases.clinician_profile_rules import as_dependents
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteSpecialtyUseCase(DeleteSpecialty):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        specialties: Specialties,
        profiles: ClinicianProfiles,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="specialty")
        self._specialties = specialties
        self._profiles = profiles

    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        self._writes.delete(
            records=self._specialties,
            actor=actor,
            record_id=record_id,
            dependents=self._dependents,
            message="Des praticiens ont encore cette spécialité.",
        )

    def _dependents(self, specialty: Specialty) -> Dependents:
        return Dependents(as_dependents(self._profiles.matching(specialty_id=specialty.id)))
