from datetime import datetime

from drlibre.scheduling.application.ports.inbound import FreeCliniciansAt
from drlibre.scheduling.application.ports.outbound import (
    SchedulingDirectory,
    SlotHolds,
    SlotQueries,
)
from drlibre.scheduling.application.use_cases.open_slots import clinicians_free_at
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class FreeCliniciansAtUseCase(FreeCliniciansAt):
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

    def execute(self, *, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None or not kind.active:
            return ()
        return clinicians_free_at(
            queries=self._queries,
            holds=self._holds,
            kind=kind,
            clinicians=self._directory.active_clinicians(kind.department_id),
            start=start,
            now=self._clock.now(),
        )
