from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import SaveRoom
from drlibre.organisation.application.ports.outbound import ClinicianProfiles, Departments, Rooms
from drlibre.organisation.application.use_cases.clinician_profile_rules import as_dependents
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.room import Room
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class SaveRoomUseCase(SaveRoom):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        rooms: Rooms,
        departments: Departments,
        profiles: ClinicianProfiles,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="room")
        self._rooms = rooms
        self._departments = departments
        self._profiles = profiles

    def execute(self, *, actor: Id | None, record_id: Id | None, fields: Mapping[str, str]) -> Id:
        return self._writes.save(
            records=self._rooms,
            build=Room.from_form,
            actor=actor,
            record_id=record_id,
            fields=fields,
            check=self._check,
        )

    def _check(self, before: Room | None, after: Room) -> None:
        if self._departments.get(after.department_id) is None:
            raise invalid_field("department_id", "Choisissez un département.")
        if before is not None and before.department_id != after.department_id:
            users = self._profiles.matching(
                department_id=before.department_id, default_room_id=before.id
            )
            Dependents(as_dependents(users)).refuse_if_any(
                "Des praticiens de l'ancien département utilisent cette salle par défaut."
            )
