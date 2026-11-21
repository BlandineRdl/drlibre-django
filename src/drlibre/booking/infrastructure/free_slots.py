from datetime import datetime

from drlibre.booking.application.ports.outbound import FreeSlots
from drlibre.scheduling.application.ports.inbound import FreeCliniciansAt, IsSlotFree
from drlibre.shared_kernel.ids import Id


class SchedulingFreeSlots(FreeSlots):
    """Asks scheduling's slot use cases, so a booking accepts exactly the slots shown."""

    def __init__(self, is_slot_free: IsSlotFree, free_clinicians_at: FreeCliniciansAt) -> None:
        self._is_slot_free = is_slot_free
        self._free_clinicians_at = free_clinicians_at

    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
        ignoring_appointment: Id | None = None,
    ) -> bool:
        return self._is_slot_free.execute(
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            start=start,
            ignoring_hold=ignoring_hold,
            ignoring_appointment=ignoring_appointment,
        )

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        return self._free_clinicians_at.execute(
            appointment_type_id=appointment_type_id, start=start
        )
