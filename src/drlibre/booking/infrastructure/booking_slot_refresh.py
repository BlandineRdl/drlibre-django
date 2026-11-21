from drlibre.booking.application.ports.outbound import SlotRefresh
from drlibre.scheduling.application.ports.inbound import RefreshSlots
from drlibre.shared_kernel.ids import Id


class BookingSlotRefresh(SlotRefresh):
    """Hands the clinician to scheduling's RefreshSlots, in the caller's unit of work."""

    def __init__(self, refresh: RefreshSlots) -> None:
        self._refresh = refresh

    def refresh(self, clinician_id: Id) -> None:
        self._refresh.execute(clinician_id=clinician_id)
