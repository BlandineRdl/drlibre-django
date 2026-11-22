from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import FREE_ONLY, FindSlotStates
from drlibre.scheduling.application.ports.outbound import (
    AvailabilityRules,
    ClinicianAppointments,
    SchedulingDirectory,
    SlotHolds,
    TimeOffs,
)
from drlibre.scheduling.application.use_cases.computed_slots import slot_horizon
from drlibre.scheduling.application.use_cases.find_free_slots import (
    FreeSlotRead,
    OpenSlots,
)
from drlibre.scheduling.domain.slot import Period, Slot, SlotState, SlotStatus
from drlibre.scheduling.domain.slot_engine import SlotEngine
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

STAFF_ONLY = "Seul le personnel voit les créneaux occupés."


class FindSlotStatesUseCase(FindSlotStates):
    def __init__(
        self,
        *,
        read: FreeSlotRead,
        directory: SchedulingDirectory,
        rules: AvailabilityRules,
        time_offs: TimeOffs,
        appointments: ClinicianAppointments,
        holds: SlotHolds,
    ) -> None:
        self._read = read
        self._directory = directory
        self._rules = rules
        self._time_offs = time_offs
        self._appointments = appointments
        self._holds = holds

    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        end: datetime,
        statuses: frozenset[SlotStatus] = FREE_ONLY,
        staff: bool = False,
    ) -> tuple[SlotState, ...]:
        wanted = statuses or FREE_ONLY
        if wanted != FREE_ONLY and not staff:
            raise DomainError(ErrorCode.FORBIDDEN, STAFF_ONLY)
        read = self._read.open(
            appointment_type_id=appointment_type_id,
            clinician_id=clinician_id,
            start=start,
            end=end,
        )
        states: list[SlotState] = []
        for clinician in read.clinicians:
            free = tuple(s.slot for s in read.found if s.clinician_id == clinician)
            if free or wanted != FREE_ONLY:
                states += self._states(read, clinician, free, wanted)
        return tuple(sorted(states, key=lambda s: (s.start, str(s.clinician_id))))

    def _states(
        self,
        read: OpenSlots,
        clinician_id: Id,
        free: tuple[Slot, ...],
        wanted: frozenset[SlotStatus],
    ) -> list[SlotState]:
        clinician = self._directory.clinician(clinician_id)
        if clinician is None:
            return []
        engine = SlotEngine(
            rules=self._rules.for_clinician(clinician_id),
            time_off=(),
            busy=(),
            duration=timedelta(minutes=read.kind.duration_minutes),
            buffer=timedelta(minutes=read.kind.buffer_minutes),
            time_zone=ZoneInfo(clinician.time_zone),
        )
        marked = [(s, SlotStatus.FREE) for s in free] if SlotStatus.FREE in wanted else []
        if wanted - FREE_ONLY:
            taken = self._taken(read, clinician_id, engine, {s.start for s in free})
            marked += [(s, status) for s, status in taken if status in wanted]
        return [
            SlotState(clinician_id, rule.id, slot.start, slot.end, status)
            for slot, status in marked
            if (rule := engine.rule_of(slot)) is not None
        ]

    def _taken(
        self, read: OpenSlots, clinician_id: Id, engine: SlotEngine, free: set[datetime]
    ) -> list[tuple[Slot, SlotStatus]]:
        """The rules' starts within the stored range that are not free, with what takes them."""
        horizon = slot_horizon(read.now, engine.time_zone)
        start = max(read.within.start, horizon.start, read.now)
        end = min(read.within.end, horizon.end)
        if end <= start:
            return []
        within = Period(start, end)
        buffer = engine.buffer
        around = Period(start - buffer, end)
        offs = [t.period for t in self._time_offs.for_clinician(clinician_id)]
        booked = [
            a.period.extended(buffer)
            for a in self._appointments.for_clinician(clinician_id, within=around)
            if a.active
        ]
        held = [
            h.period.extended(buffer)
            for h in self._holds.open((clinician_id,), within=around, at=read.now, ignoring=None)
        ]
        found: list[tuple[Slot, SlotStatus]] = []
        for slot in engine.free_slots(within):
            if slot.start in free:
                continue
            for status, periods in (
                (SlotStatus.UNAVAILABLE, offs),
                (SlotStatus.BUSY, booked),
                (SlotStatus.TENTATIVE, held),
            ):
                if any(p.overlaps(slot.period) for p in periods):
                    found.append((slot, status))
                    break
        return found
