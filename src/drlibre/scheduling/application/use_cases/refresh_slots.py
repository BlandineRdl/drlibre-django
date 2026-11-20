from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import RefreshSlots
from drlibre.scheduling.application.ports.outbound import (
    ActiveAppointments,
    AvailabilityRules,
    SchedulingDirectory,
    SlotStore,
    StoredSlot,
    TimeOffs,
)
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.domain.slot_engine import SlotEngine
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id

HORIZON_DAYS = 90


class RefreshSlotsUseCase(RefreshSlots):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: SchedulingDirectory,
        rules: AvailabilityRules,
        time_offs: TimeOffs,
        appointments: ActiveAppointments,
        store: SlotStore,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._rules = rules
        self._time_offs = time_offs
        self._appointments = appointments
        self._store = store

    def execute(self, *, clinician_id: Id) -> None:
        clinician = self._directory.clinician(clinician_id)
        if clinician is None:
            self._store.replace(clinician_id, ())
            return
        tz = ZoneInfo(clinician.time_zone)
        window = _horizon(self._clock.now(), tz)
        types = self._directory.appointment_types(clinician.department_id)
        lead = timedelta(minutes=max((t.buffer_minutes for t in types), default=0))
        busy = self._appointments.for_clinician(
            clinician_id, within=Period(window.start - lead, window.end)
        )
        rules = self._rules.for_clinician(clinician_id)
        time_off = self._time_offs.for_clinician(clinician_id)
        stored = tuple(
            StoredSlot(clinician_id, kind.id, slot)
            for kind in types
            for slot in SlotEngine(
                rules=rules,
                time_off=time_off,
                busy=busy,
                duration=timedelta(minutes=kind.duration_minutes),
                buffer=timedelta(minutes=kind.buffer_minutes),
                time_zone=tz,
            ).free_slots(window)
        )
        self._store.replace(clinician_id, stored)


def _horizon(now: datetime, tz: ZoneInfo) -> Period:
    # From local midnight today through the last local day of the horizon.
    today = now.astimezone(tz).date()
    start = datetime.combine(today, time(), tzinfo=tz).astimezone(UTC)
    end = datetime.combine(today + timedelta(days=HORIZON_DAYS + 1), time(), tzinfo=tz)
    return Period(start, end.astimezone(UTC))
