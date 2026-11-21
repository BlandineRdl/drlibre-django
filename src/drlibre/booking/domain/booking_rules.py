from datetime import datetime
from enum import StrEnum

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.shared_kernel.booking_policy import (
    BOOKING_LEAD_TIME,
    CANCELLATION_WINDOW,
    MAX_OPEN_ONLINE,
)


class BookingRule(StrEnum):
    LEAD_TIME_TOO_SHORT = "lead_time_too_short"
    TOO_MANY_OPEN_BOOKINGS = "too_many_open_bookings"
    TYPE_NOT_BOOKABLE_ONLINE = "type_not_bookable_online"
    OUTSIDE_AVAILABILITY = "outside_availability"
    CANCELLATION_WINDOW_CLOSED = "cancellation_window_closed"


class PatientAction(StrEnum):
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"


class ClinicianAction(StrEnum):
    CHECK_IN = "check_in"
    COMPLETE = "complete"
    NO_SHOW = "no_show"
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"


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
    if for_patient and start < now + BOOKING_LEAD_TIME:
        broken.append(BookingRule.LEAD_TIME_TOO_SHORT)
    if for_patient and open_online_count >= MAX_OPEN_ONLINE:
        broken.append(BookingRule.TOO_MANY_OPEN_BOOKINGS)
    if for_patient and not type_online:
        broken.append(BookingRule.TYPE_NOT_BOOKABLE_ONLINE)
    if not is_free_slot:
        broken.append(BookingRule.OUTSIDE_AVAILABILITY)
    return tuple(broken)


def cancel_violations(*, start: datetime, now: datetime) -> tuple[BookingRule, ...]:
    """cancellation_window_closed when the appointment starts within 24 hours."""
    if start < now + CANCELLATION_WINDOW:
        return (BookingRule.CANCELLATION_WINDOW_CLOSED,)
    return ()


def reschedule_violations(
    *,
    for_patient: bool,
    current_start: datetime,
    new_start: datetime,
    now: datetime,
    type_online: bool,
    is_free_slot: bool,
) -> tuple[BookingRule, ...]:
    """Spec 5.3 rules a reschedule breaks, in order; staff are bound only by availability."""
    if not for_patient:
        return () if is_free_slot else (BookingRule.OUTSIDE_AVAILABILITY,)
    broken = list(cancel_violations(start=current_start, now=now))
    if new_start < now + BOOKING_LEAD_TIME:
        broken.append(BookingRule.LEAD_TIME_TOO_SHORT)
    if not type_online:
        broken.append(BookingRule.TYPE_NOT_BOOKABLE_ONLINE)
    if not is_free_slot:
        broken.append(BookingRule.OUTSIDE_AVAILABILITY)
    return tuple(broken)


def allowed_actions(
    appointment: Appointment, now: datetime, *, type_online: bool
) -> frozenset[PatientAction]:
    """The changes a patient may ask for now, so a page offers only those."""
    if cancel_violations(start=appointment.start, now=now):
        return frozenset()
    allowed = set[PatientAction]()
    if appointment.cancellable:
        allowed.add(PatientAction.CANCEL)
    if appointment.movable and type_online:
        allowed.add(PatientAction.RESCHEDULE)
    return frozenset(allowed)


def clinician_actions(appointment: Appointment) -> frozenset[ClinicianAction]:
    """The changes the appointment's clinician may make in its current status."""
    allowed = set[ClinicianAction]()
    if appointment.status is AppointmentStatus.BOOKED:
        allowed |= {ClinicianAction.CHECK_IN, ClinicianAction.NO_SHOW}
    if appointment.status is AppointmentStatus.CHECKED_IN:
        allowed.add(ClinicianAction.COMPLETE)
    if appointment.cancellable:
        allowed.add(ClinicianAction.CANCEL)
    if appointment.movable:
        allowed.add(ClinicianAction.RESCHEDULE)
    return frozenset(allowed)
