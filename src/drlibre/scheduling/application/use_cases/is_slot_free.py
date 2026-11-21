from datetime import datetime

from drlibre.scheduling.application.ports.inbound import IsSlotFree
from drlibre.scheduling.application.ports.outbound import (
    SchedulingDirectory,
    SlotHolds,
    SlotQueries,
)
from drlibre.scheduling.application.use_cases.open_slots import clinicians_free_at
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class IsSlotFreeUseCase(IsSlotFree):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: SchedulingDirectory,
        queries: SlotQueries,
        holds: SlotHolds,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._queries = queries
        self._holds = holds

    def execute(
        self,
        *,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        ignoring_hold: Id | None,
    ) -> bool:
        clinician = self._directory.clinician(clinician_id)
        kind = self._directory.appointment_type(appointment_type_id)
        if clinician is None or not clinician.active or kind is None or not kind.active:
            return False
        free = clinicians_free_at(
            queries=self._queries,
            holds=self._holds,
            kind=kind,
            clinicians=(clinician_id,),
            start=start,
            now=self._clock.now(),
            ignoring_hold=ignoring_hold,
        )
        return bool(free)
