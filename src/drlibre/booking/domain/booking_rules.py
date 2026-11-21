from datetime import datetime, timedelta
from enum import StrEnum

LEAD_TIME = timedelta(minutes=120)
CANCELLATION_WINDOW = timedelta(hours=24)
MAX_OPEN_ONLINE = 3


class BookingRule(StrEnum):
    LEAD_TIME_TOO_SHORT = "lead_time_too_short"
    TOO_MANY_OPEN_BOOKINGS = "too_many_open_bookings"
    TYPE_NOT_BOOKABLE_ONLINE = "type_not_bookable_online"
    OUTSIDE_AVAILABILITY = "outside_availability"


def violations(
    *,
    for_patient: bool,
    start: datetime,
    now: datetime,
    type_online: bool,
    open_online_count: int,
    is_free_slot: bool,
) -> tuple[BookingRule, ...]:
    """Spec 5.3 rules broken, in the spec's order; patient-only rules skipped for staff."""
    broken: list[BookingRule] = []
    if for_patient and start < now + LEAD_TIME:
        broken.append(BookingRule.LEAD_TIME_TOO_SHORT)
    if for_patient and open_online_count >= MAX_OPEN_ONLINE:
        broken.append(BookingRule.TOO_MANY_OPEN_BOOKINGS)
    if for_patient and not type_online:
        broken.append(BookingRule.TYPE_NOT_BOOKABLE_ONLINE)
    if not is_free_slot:
        broken.append(BookingRule.OUTSIDE_AVAILABILITY)
    return tuple(broken)
