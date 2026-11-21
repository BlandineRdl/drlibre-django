from datetime import datetime

from drlibre.booking.application.ports.outbound import FreeSlots
from drlibre.scheduling.application.ports.inbound import SlotAvailability
from drlibre.shared_kernel.ids import Id


class SchedulingFreeSlots(FreeSlots):
    """Asks scheduling's SlotAvailability, so a booking accepts exactly the slots shown."""

    def __init__(self, availability: SlotAvailability) -> None:
        self._availability = availability

    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
    ) -> bool:
        return self._availability.is_free(
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            start=start,
            ignoring_hold=ignoring_hold,
        )

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        return self._availability.free_clinicians(
            appointment_type_id=appointment_type_id, start=start
        )
