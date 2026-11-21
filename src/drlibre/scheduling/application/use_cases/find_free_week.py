from datetime import date

from drlibre.scheduling.application.ports.inbound import FindFreeSlots, FindFreeWeek, FreeWeek
from drlibre.scheduling.application.ports.outbound import SchedulingDirectory
from drlibre.scheduling.domain.week import Week
from drlibre.shared_kernel.booking_policy import BOOKING_LEAD_TIME
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class FindFreeWeekUseCase(FindFreeWeek):
    def __init__(
        self, *, clock: Clock, directory: SchedulingDirectory, find_free_slots: FindFreeSlots
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._find_free_slots = find_free_slots

    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id,
        week: date | None,
        ignoring_appointment: Id | None = None,
    ) -> FreeWeek:
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Type de RDV introuvable.")
        now = self._clock.now()
        window = Week.within_horizon(asked=week, now=now, time_zone=kind.time_zone)
        slots = self._find_free_slots.execute(
            appointment_type_id=appointment_type_id,
            clinician_id=clinician_id,
            # Like search, offer only slots the lead time rule accepts.
            start=max(window.start, now + BOOKING_LEAD_TIME),
            end=window.end,
            ignoring_appointment=ignoring_appointment,
        )
        return FreeWeek(
            monday=window.monday,
            previous_monday=window.previous,
            next_monday=window.following,
            time_zone=kind.time_zone,
            slots=slots,
        )
