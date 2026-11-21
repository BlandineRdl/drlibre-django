from datetime import datetime

from drlibre.booking.application.ports.inbound import HeldPeriod, OpenHolds
from drlibre.booking.application.ports.outbound import Holds
from drlibre.shared_kernel.ids import Id


class OpenHoldsUseCase(OpenHolds):
    def __init__(self, *, holds: Holds) -> None:
        self._holds = holds

    def execute(
        self, *, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, at: datetime
    ) -> tuple[HeldPeriod, ...]:
        found = self._holds.open_in(clinician_ids, start, end, at=at)
        return tuple(HeldPeriod(h.id, h.clinician_id, h.start, h.end) for h in found)
