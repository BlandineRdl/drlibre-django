from drlibre.organisation.application.ports.outbound import SlotRefresh
from drlibre.scheduling.application.ports.inbound import RefreshSlots
from drlibre.shared_kernel.ids import Id


class SchedulingSlotRefresh(SlotRefresh):
    """Hands each profile to scheduling's RefreshSlots, in the caller's unit of work."""

    def __init__(self, *, refresh: RefreshSlots) -> None:
        self._refresh = refresh

    def refresh(self, profile_ids: tuple[Id, ...]) -> None:
        for profile_id in profile_ids:
            self._refresh.execute(clinician_id=profile_id)
