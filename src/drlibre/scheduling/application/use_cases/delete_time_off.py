from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.scheduling.application.ports.inbound import DeleteTimeOff, RefreshSlots
from drlibre.scheduling.application.ports.outbound import SchedulingDirectory, TimeOffs
from drlibre.scheduling.application.use_cases.clinician_writes import ClinicianWrites
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteTimeOffUseCase(DeleteTimeOff):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: SchedulingDirectory,
        time_offs: TimeOffs,
        refresh: RefreshSlots,
    ) -> None:
        self._time_offs = time_offs
        self._writes = ClinicianWrites(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            refresh=refresh,
            entity_type="time_off",
        )

    def execute(self, *, actor: Id, time_off_id: Id) -> None:
        clinician = self._writes.caller(actor)
        time_off = self._writes.owned(self._time_offs.get(time_off_id), time_off_id, clinician)
        self._writes.commit(
            actor=actor,
            clinician=clinician,
            action="deleted",
            entity_id=time_off.id,
            metadata={},
            write=lambda: self._time_offs.delete(time_off.id),
        )
