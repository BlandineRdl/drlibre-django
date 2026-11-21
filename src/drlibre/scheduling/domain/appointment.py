from dataclasses import dataclass
from enum import StrEnum

from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


class AppointmentStatus(StrEnum):
    BOOKED = "BOOKED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


@dataclass(frozen=True, slots=True)
class Appointment:
    """A clinician's appointment as slots see it: when, and whether it still holds the time."""

    id: Id
    period: Period
    status: AppointmentStatus

    @property
    def active(self) -> bool:
        return self.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)
