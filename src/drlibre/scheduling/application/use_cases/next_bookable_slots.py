from drlibre.scheduling.application.ports.inbound import FindFreeSlots, NextBookableSlots
from drlibre.scheduling.domain.slot import Slot
from drlibre.shared_kernel.booking_policy import ALTERNATIVES_WINDOW, BOOKING_LEAD_TIME
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id


class NextBookableSlotsUseCase(NextBookableSlots):
    def __init__(self, *, clock: Clock, find_free_slots: FindFreeSlots) -> None:
        self._clock = clock
        self._find_free_slots = find_free_slots

    def execute(self, *, appointment_type_id: Id, clinician_id: Id | None) -> tuple[Slot, ...]:
        start = self._clock.now() + BOOKING_LEAD_TIME
        try:
            return self._find_free_slots.execute(
                appointment_type_id=appointment_type_id,
                clinician_id=clinician_id,
                start=start,
                end=start + ALTERNATIVES_WINDOW,
            )
        except DomainError:
            return ()
