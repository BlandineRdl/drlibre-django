import dataclasses
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import ClinicianEntry
from drlibre.booking.application.ports.outbound import BookingDirectory
from drlibre.booking.domain.booking_rules import clinician_actions
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

ONE_DAY = timedelta(days=1)


def time_zone_of(directory: BookingDirectory, profile_id: Id) -> str:
    venue = directory.venue(profile_id)
    if venue is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
    return venue.time_zone


def day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    return datetime.combine(day, time(), zone), datetime.combine(day + ONE_DAY, time(), zone)


def with_actions(entry: ClinicianEntry) -> ClinicianEntry:
    return dataclasses.replace(entry, actions=clinician_actions(entry.appointment))
