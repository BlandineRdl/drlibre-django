from datetime import datetime, timedelta

from drlibre.scheduling.application.ports.inbound import SlotAvailability
from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    SchedulingDirectory,
    SlotHolds,
    SlotQueries,
)
from drlibre.scheduling.application.use_cases.open_slots import open_slots
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class SlotAvailabilityUseCase(SlotAvailability):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: SchedulingDirectory,
        queries: SlotQueries,
        holds: SlotHolds,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._queries = queries
        self._holds = holds

    def is_free(
        self,
        *,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        ignoring_hold: Id | None,
    ) -> bool:
        clinician = self._directory.clinician(clinician_id)
        kind = self._directory.appointment_type(appointment_type_id)
        if clinician is None or not clinician.active or kind is None or not kind.active:
            return False
        return bool(self._at(kind, (clinician_id,), start, ignoring_hold))

    def free_clinicians(self, *, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None or not kind.active:
            return ()
        clinicians = self._directory.active_clinicians(kind.department_id)
        return self._at(kind, clinicians, start, None)

    def _at(
        self,
        kind: AppointmentType,
        clinicians: tuple[Id, ...],
        start: datetime,
        ignoring: Id | None,
    ) -> tuple[Id, ...]:
        within = Period(start, start + timedelta(minutes=kind.duration_minutes))
        slots = open_slots(
            queries=self._queries,
            holds=self._holds,
            kind=kind,
            clinicians=clinicians,
            within=within,
            now=self._clock.now(),
            ignoring_hold=ignoring,
        )
        return tuple(dict.fromkeys(s.clinician_id for s in slots if s.slot.start == start))
