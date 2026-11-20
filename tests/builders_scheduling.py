from datetime import date, datetime, time

from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.ids import Id


def rule(
    clinician_id: Id,
    *,
    weekday: int,
    start: time = time(9),
    end: time = time(12),
    step_minutes: int = 15,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
) -> AvailabilityRule:
    return AvailabilityRule(
        id=Id(),
        clinician_id=clinician_id,
        weekday=weekday,
        start=start,
        end=end,
        step_minutes=step_minutes,
        room_id=None,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def time_off(clinician_id: Id, start: datetime, end: datetime) -> TimeOff:
    return TimeOff(id=Id(), clinician_id=clinician_id, start=start, end=end, reason="Congés")


def appointment(
    clinician_id: Id, start: datetime, end: datetime, *, status: str = "BOOKED"
) -> tuple[Id, Period, str]:
    return clinician_id, Period(start, end), status
