from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    AvailabilityRules,
    ClinicianAppointments,
    ClinicianSlot,
    SchedulingDirectory,
    StoredSlot,
    TimeOffs,
)
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.domain.slot_engine import SlotEngine
from drlibre.shared_kernel.booking_policy import SLOT_HORIZON_DAYS
from drlibre.shared_kernel.ids import Id


class SlotComputation:
    """Spec 5.1 slots computed from rules, time off and appointments, not from the stored table."""

    def __init__(
        self,
        *,
        directory: SchedulingDirectory,
        rules: AvailabilityRules,
        time_offs: TimeOffs,
        appointments: ClinicianAppointments,
    ) -> None:
        self._directory = directory
        self._rules = rules
        self._time_offs = time_offs
        self._appointments = appointments

    def slots(
        self,
        clinician_id: Id,
        kinds: tuple[AppointmentType, ...],
        window: Period,
        *,
        time_zone: ZoneInfo,
        ignoring: Id | None = None,
    ) -> tuple[StoredSlot, ...]:
        """Free slots of each type inside the window, the ignored appointment left out."""
        lead = timedelta(minutes=max((k.buffer_minutes for k in kinds), default=0))
        booked = self._appointments.for_clinician(
            clinician_id, within=Period(window.start - lead, window.end)
        )
        busy = tuple(a.period for a in booked if a.active and a.id != ignoring)
        rules = self._rules.for_clinician(clinician_id)
        time_off = self._time_offs.for_clinician(clinician_id)
        return tuple(
            StoredSlot(clinician_id, kind.id, slot)
            for kind in kinds
            for slot in SlotEngine(
                rules=rules,
                time_off=time_off,
                busy=busy,
                duration=timedelta(minutes=kind.duration_minutes),
                buffer=timedelta(minutes=kind.buffer_minutes),
                time_zone=time_zone,
            ).free_slots(window)
        )

    def ignoring(
        self,
        appointment_id: Id,
        *,
        kind: AppointmentType,
        clinicians: tuple[Id, ...],
        within: Period,
        now: datetime,
    ) -> tuple[ClinicianSlot, ...]:
        """What the stored table would hold inside the range from now without the appointment."""
        found: list[ClinicianSlot] = []
        for clinician_id in clinicians:
            clinician = self._directory.clinician(clinician_id)
            if clinician is None:
                continue
            tz = ZoneInfo(clinician.time_zone)
            horizon = slot_horizon(now, tz)
            start, end = max(within.start, horizon.start), min(within.end, horizon.end)
            if end <= start:
                continue
            computed = self.slots(
                clinician_id, (kind,), Period(start, end), time_zone=tz, ignoring=appointment_id
            )
            found.extend(
                ClinicianSlot(clinician_id, s.slot) for s in computed if s.slot.start >= now
            )
        return tuple(sorted(found, key=lambda c: (c.slot.start, str(c.clinician_id))))


def slot_horizon(now: datetime, tz: ZoneInfo) -> Period:
    """From local midnight today through the last local day of the horizon."""
    today = now.astimezone(tz).date()
    start = datetime.combine(today, time(), tzinfo=tz).astimezone(UTC)
    end = datetime.combine(today + timedelta(days=SLOT_HORIZON_DAYS + 1), time(), tzinfo=tz)
    return Period(start, end.astimezone(UTC))
