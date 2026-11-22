from datetime import datetime, timedelta

from drlibre.scheduling.application.ports.inbound import (
    FREE_ONLY,
    FindSlotStates,
    ReadSlotState,
)
from drlibre.scheduling.application.ports.outbound import SchedulingDirectory
from drlibre.scheduling.domain.slot import SlotState, SlotStatus
from drlibre.shared_kernel.ids import Id


class ReadSlotStateUseCase(ReadSlotState):
    def __init__(self, *, directory: SchedulingDirectory, find_slot_states: FindSlotStates):
        self._directory = directory
        self._find = find_slot_states

    def execute(
        self, *, appointment_type_id: Id, clinician_id: Id, start: datetime, staff: bool = False
    ) -> SlotState | None:
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None:
            return None
        found = self._find.execute(
            appointment_type_id=appointment_type_id,
            clinician_id=clinician_id,
            start=start,
            end=start + timedelta(minutes=kind.duration_minutes),
            statuses=frozenset(SlotStatus) if staff else FREE_ONLY,
            staff=staff,
        )
        return next((s for s in found if s.start == start), None)
