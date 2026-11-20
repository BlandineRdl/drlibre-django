from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import DeleteDepartment
from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    ClinicianProfiles,
    Departments,
    Rooms,
)
from drlibre.organisation.application.use_cases.clinician_profile_rules import as_dependents
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.department import Department
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependent, Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteDepartmentUseCase(DeleteDepartment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        departments: Departments,
        rooms: Rooms,
        appointment_types: AppointmentTypes,
        profiles: ClinicianProfiles,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="department")
        self._departments = departments
        self._rooms = rooms
        self._appointment_types = appointment_types
        self._profiles = profiles

    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        self._writes.delete(
            records=self._departments,
            actor=actor,
            record_id=record_id,
            dependents=self._dependents,
            message="Ce département a encore des praticiens, des salles ou des types de RDV.",
        )

    def _dependents(self, department: Department) -> Dependents:
        rooms = self._rooms.for_department(department.id)
        types = self._appointment_types.for_department(department.id)
        return Dependents.of(
            as_dependents(self._profiles.matching(department_id=department.id)),
            tuple(Dependent("room", r.id, r.label) for r in rooms),
            tuple(Dependent("appointment_type", t.id, t.label) for t in types),
        )
