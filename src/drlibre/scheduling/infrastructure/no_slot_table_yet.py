from drlibre.scheduling.application.ports.outbound import SlotStore, StoredSlot
from drlibre.shared_kernel.ids import Id


class NoSlotTableYet(SlotStore):
    """Null adapter until the PostgreSQL slot table (E2 phase 3) stores refreshed slots."""

    def replace(self, clinician_id: Id, slots: tuple[StoredSlot, ...]) -> None:
        return None
