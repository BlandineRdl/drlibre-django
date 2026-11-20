from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.organisation.application.ports.inbound import DeleteRoom
from drlibre.organisation.application.ports.outbound import (
    ClinicianProfiles,
    Rooms,
    ScheduleDependents,
)
from drlibre.organisation.application.use_cases.clinician_profile_rules import as_dependents
from drlibre.organisation.application.use_cases.records import RecordWrites
from drlibre.organisation.domain.room import Room
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteRoomUseCase(DeleteRoom):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        rooms: Rooms,
        schedule: ScheduleDependents,
        profiles: ClinicianProfiles,
    ) -> None:
        self._writes = RecordWrites(clock=clock, uow=uow, audit=audit, entity_type="room")
        self._rooms = rooms
        self._schedule = schedule
        self._profiles = profiles

    def execute(self, *, actor: Id | None, record_id: Id) -> None:
        self._writes.delete(
            records=self._rooms,
            actor=actor,
            record_id=record_id,
            dependents=self._dependents,
            message="Cette salle est encore utilisée.",
        )

    def _dependents(self, room: Room) -> Dependents:
        return Dependents.of(
            self._schedule.for_room(room.id),
            as_dependents(self._profiles.matching(default_room_id=room.id)),
        )
