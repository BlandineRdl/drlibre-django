from collections.abc import Mapping
from zoneinfo import ZoneInfo

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.scheduling.application.ports.inbound import RecordTimeOff, RefreshSlots
from drlibre.scheduling.application.ports.outbound import SchedulingDirectory, TimeOffs
from drlibre.scheduling.application.use_cases.clinician_writes import ClinicianWrites
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class RecordTimeOffUseCase(RecordTimeOff):
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

    def execute(self, *, actor: Id, fields: Mapping[str, str]) -> Id:
        clinician = self._writes.caller(actor)
        time_off = TimeOff.from_form(
            fields, id=Id(), clinician_id=clinician.id, time_zone=ZoneInfo(clinician.time_zone)
        )
        # The reason is free text, so it never reaches the audit metadata.
        self._writes.commit(
            actor=actor,
            clinician=clinician,
            action="created",
            entity_id=time_off.id,
            metadata={},
            write=lambda: self._save(time_off),
        )
        return time_off.id

    def _save(self, time_off: TimeOff) -> None:
        self._time_offs.lock_clinician(time_off.clinician_id)
        if any(
            time_off.same_period_as(t) for t in self._time_offs.for_clinician(time_off.clinician_id)
        ):
            raise invalid_field("start", "Une absence couvre déjà exactement cette période.")
        self._time_offs.save(time_off)
