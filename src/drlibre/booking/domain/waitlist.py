import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from drlibre.shared_kernel.booking_policy import BOOKING_LEAD_TIME
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field


class WaitlistStatus(StrEnum):
    WAITING = "WAITING"
    OFFERED = "OFFERED"
    BOOKED = "BOOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class WaitlistEntry:
    """A patient waiting for a freed slot of a type, inside [earliest, latest)."""

    id: Id
    patient_id: Id
    appointment_type_id: Id
    clinician_id: Id | None
    earliest: datetime
    latest: datetime
    status: WaitlistStatus
    created_at: datetime
    offered_appointment_id: Id | None = None

    @classmethod
    def join(
        cls,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        earliest: datetime,
        latest: datetime,
        at: datetime,
    ) -> "WaitlistEntry":
        """A WAITING entry; invalid_input on to_date when the window is empty."""
        if latest <= earliest:
            raise invalid_field("to_date", "La date de fin suit la date de début.")
        return cls(
            id=Id(),
            patient_id=patient_id,
            appointment_type_id=appointment_type_id,
            clinician_id=clinician_id,
            earliest=earliest,
            latest=latest,
            status=WaitlistStatus.WAITING,
            created_at=at,
        )

    def offered(self, appointment_id: Id) -> "WaitlistEntry":
        """OFFERED the freed appointment; invalid_transition unless WAITING."""
        self._require(WaitlistStatus.WAITING)
        return dataclasses.replace(
            self, status=WaitlistStatus.OFFERED, offered_appointment_id=appointment_id
        )

    def booked(self) -> "WaitlistEntry":
        """BOOKED, offer cleared; invalid_transition unless OFFERED."""
        self._require(WaitlistStatus.OFFERED)
        return dataclasses.replace(self, status=WaitlistStatus.BOOKED, offered_appointment_id=None)

    def back_to_waiting(self) -> "WaitlistEntry":
        """WAITING again, offer cleared; invalid_transition unless OFFERED."""
        self._require(WaitlistStatus.OFFERED)
        return dataclasses.replace(self, status=WaitlistStatus.WAITING, offered_appointment_id=None)

    def expired(self) -> "WaitlistEntry":
        """EXPIRED; invalid_transition unless WAITING."""
        self._require(WaitlistStatus.WAITING)
        return dataclasses.replace(self, status=WaitlistStatus.EXPIRED)

    def fits(self, start: datetime, end: datetime) -> bool:
        return self.earliest <= start and end <= self.latest

    def matches(
        self, appointment_type_id: Id, clinician_id: Id, start: datetime, end: datetime
    ) -> bool:
        """Same type, preferred clinician empty or equal, and the slot inside the window."""
        return (
            self.appointment_type_id == appointment_type_id
            and self.clinician_id in (None, clinician_id)
            and self.fits(start, end)
        )

    def acceptable_by_patient(self, offered_start: datetime, now: datetime) -> bool:
        """OFFERED and the offered start still at least the booking lead time ahead."""
        return self.status is WaitlistStatus.OFFERED and offered_start >= now + BOOKING_LEAD_TIME

    def acceptable_by_staff(self, offered_start: datetime, now: datetime) -> bool:
        """OFFERED and the offered start still ahead."""
        return self.status is WaitlistStatus.OFFERED and offered_start > now

    @property
    def offerable(self) -> bool:
        """Only a WAITING entry receives a manual offer."""
        return self.status is WaitlistStatus.WAITING

    def _require(self, status: WaitlistStatus) -> None:
        if self.status is not status:
            raise DomainError(
                ErrorCode.INVALID_TRANSITION,
                "Cette entrée d'attente ne permet pas ce changement.",
                {"status": self.status.value},
            )


def oldest(entries: Iterable[WaitlistEntry]) -> WaitlistEntry | None:
    """The entry joined first, the lowest id breaking ties."""
    return min(entries, key=lambda e: (e.created_at, e.id.value), default=None)
