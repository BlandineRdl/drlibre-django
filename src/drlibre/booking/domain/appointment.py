import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

# A cancellation reason holds at most this many characters (spec §3.1).
MAX_CANCELLATION_REASON = 500


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

    @property
    def cancellable(self) -> bool:
        return self.status in (AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN)

    @property
    def movable(self) -> bool:
        return self.status is AppointmentStatus.BOOKED

    def cancelled(self, *, at: datetime, reason: str) -> "Appointment":
        """CANCELLED at the instant for the stripped reason; invalid_input, invalid_transition."""
        cleaned = reason.strip()
        if not cleaned:
            raise invalid_field("reason", "Ce champ est obligatoire.")
        if len(cleaned) > MAX_CANCELLATION_REASON:
            raise invalid_field("reason", f"{MAX_CANCELLATION_REASON} caractères au plus.")
        if not self.cancellable:
            raise self._refused_transition()
        return dataclasses.replace(
            self,
            status=AppointmentStatus.CANCELLED,
            cancelled_at=at,
            cancellation_reason=cleaned,
        )

    def require_movable(self) -> None:
        """invalid_transition with the current status unless the appointment is BOOKED."""
        if not self.movable:
            raise self._refused_transition()

    def moved(self, *, start: datetime, duration: timedelta, room_id: Id | None) -> "Appointment":
        """The BOOKED appointment at the new start, its end recomputed from the duration."""
        self.require_movable()
        return dataclasses.replace(self, start=start, end=start + duration, room_id=room_id)

    def _refused_transition(self) -> DomainError:
        return DomainError(
            ErrorCode.INVALID_TRANSITION,
            "Ce rendez-vous ne permet pas ce changement.",
            {"status": self.status.value},
        )
