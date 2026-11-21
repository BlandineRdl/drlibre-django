from dataclasses import dataclass
from datetime import datetime, timedelta

from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.shared_kernel.ids import Id

HOLD_LIFETIME = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class BookingHold:
    """A slot kept for a visitor while their email code is pending."""

    id: Id
    clinician_id: Id
    appointment_type_id: Id
    start: datetime
    end: datetime
    source: Source
    details: VisitorDetails
    expires_at: datetime

    @classmethod
    def open(
        cls,
        *,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        duration: timedelta,
        source: Source,
        details: VisitorDetails,
        at: datetime,
    ) -> "BookingHold":
        return cls(
            id=Id(),
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            start=start,
            end=start + duration,
            source=source,
            details=details,
            expires_at=at + HOLD_LIFETIME,
        )

    @property
    def email(self) -> str:
        return self.details.email

    def is_open(self, at: datetime) -> bool:
        return at < self.expires_at

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self.start < end and start < self.end
