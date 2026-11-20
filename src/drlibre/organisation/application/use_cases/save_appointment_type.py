from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveAppointmentType
from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    ClinicianProfiles,
    Departments,
    SlotRefresh,
)
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
        profiles: ClinicianProfiles,
        slots: SlotRefresh,
    ) -> None:
        self._writes = RecordWrites(
            clock=clock, uow=uow, audit=audit, entity_type="appointment_type"
        )
        self._appointment_types = appointment_types
        self._departments = departments
        self._profiles = profiles
        self._slots = slots

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._appointment_types,
            build=AppointmentType.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
            check=self._check,
            written=self._refresh,
        )

    def _check(self, before: AppointmentType | None, after: AppointmentType) -> None:
        if self._departments.get(after.department_id) is None:
            raise invalid_field("department_id", "Choisissez un département.")

    def _refresh(self, before: AppointmentType | None, after: AppointmentType) -> None:
        # Duration, buffer or department change every slot of both departments' clinicians.
        departments = {after.department_id} | ({before.department_id} if before else set())
        self._slots.refresh(
            tuple(
                profile.id
                for department_id in departments
                for profile in self._profiles.matching(department_id=department_id)
            )
        )
