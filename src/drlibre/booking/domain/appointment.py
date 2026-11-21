from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from drlibre.shared_kernel.ids import Id


class AppointmentStatus(StrEnum):
    BOOKED = "BOOKED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class Source(StrEnum):
    ONLINE = "ONLINE"
    ROUND_ROBIN = "ROUND_ROBIN"
    STAFF = "STAFF"


@dataclass(frozen=True, slots=True)
class Appointment:
    id: Id
    patient_id: Id
    clinician_id: Id
    appointment_type_id: Id
    room_id: Id | None
    start: datetime
    end: datetime
    status: AppointmentStatus
    source: Source
    reason: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None

    @classmethod
    def book(
        cls,
        *,
        patient_id: Id,
        clinician_id: Id,
        appointment_type_id: Id,
        room_id: Id | None,
        start: datetime,
        duration: timedelta,
        source: Source,
        reason: str | None = None,
    ) -> "Appointment":
        """A new BOOKED appointment whose end is the start plus the type's duration."""
        return cls(
            id=Id(),
            patient_id=patient_id,
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            room_id=room_id,
            start=start,
            end=start + duration,
            status=AppointmentStatus.BOOKED,
            source=source,
            reason=reason,
        )

    @property
    def active(self) -> bool:
        return self.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)
