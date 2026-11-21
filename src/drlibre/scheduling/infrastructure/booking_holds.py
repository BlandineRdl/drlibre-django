from datetime import datetime

from drlibre.booking.application.ports.inbound import OpenHolds
from drlibre.scheduling.application.ports.outbound import HeldPeriod, SlotHolds
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class BookingSlotHolds(SlotHolds):
    """Reads open holds through booking's inbound port."""

    def __init__(self, holds: OpenHolds) -> None:
        self._holds = holds

    def open(
        self, clinician_ids: tuple[Id, ...], *, within: Period, at: datetime, ignoring: Id | None
    ) -> tuple[HeldPeriod, ...]:
        found = self._holds.execute(
            clinician_ids=clinician_ids, start=within.start, end=within.end, at=at
        )
        return tuple(
            HeldPeriod(h.clinician_id, Period(h.start, h.end))
            for h in found
            if h.hold_id != ignoring
        )
