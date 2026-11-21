from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id

__all__ = [
    "Appointment",
    "BookAppointment",
    "CreateHold",
    "ExpireHolds",
    "HeldPeriod",
    "HoldCreated",
    "OpenHolds",
    "ResendCode",
    "VerifiedBooking",
    "VerifyHold",
]


class BookAppointment(Protocol):
    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        """Book for the signed-in patient, the first available clinician when none is named.

        Refused with not_found, conflict, rule_violation, no_room_available or
        no_clinician_available, writing nothing; the end time and the room are never accepted.
        """
        ...


@dataclass(frozen=True, slots=True)
class HoldCreated:
    hold_id: Id
    clinician_id: Id
    expires_at: datetime


class CreateHold(Protocol):
    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        full_name: str,
        birth_date: str,
        email: str,
        phone: str,
        reason: str,
        accepted_terms: bool,
        network: str,
    ) -> HoldCreated:
        """Hold the slot 10 minutes for the email and send it a code, replacing its open hold.

        Refused with invalid_input, not_found, conflict, rule_violation (a rule, or
        too_many_requests past 3 holds an hour per email or 20 per network address); nothing
        about any patient is returned.
        """
        ...


@dataclass(frozen=True, slots=True)
class VerifiedBooking:
    """The outcome of a correct code: a session always, then the appointment or why not."""

    token: str
    expires_at: datetime
    appointment: Appointment | None
    failure: DomainError | None


class VerifyHold(Protocol):
    def execute(self, *, hold_id: Id, code: str, user_agent: str) -> VerifiedBooking:
        """Check the code, then book for the patient of the hold's email and open their session.

        A wrong, expired or exhausted code raises invalid_input on `code`; an unknown or expired
        hold raises not_found; a staff or inactive email raises forbidden, creating nothing. A
        placement refused after a correct code keeps the account and session and is returned
        as the failure.
        """
        ...


class ResendCode(Protocol):
    def execute(self, *, hold_id: Id, network: str) -> None:
        """Void the previous code and send a new one, the hold's expiry unchanged.

        Refused with not_found for an unknown or expired hold, rule_violation too_many_requests
        past 3 an hour per email or 20 per network address.
        """
        ...


class ExpireHolds(Protocol):
    def execute(self) -> int:
        """Delete expired holds and their codes, auditing each; returns how many."""
        ...


@dataclass(frozen=True, slots=True)
class HeldPeriod:
    hold_id: Id
    clinician_id: Id
    start: datetime
    end: datetime


class OpenHolds(Protocol):
    def execute(
        self, *, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, at: datetime
    ) -> tuple[HeldPeriod, ...]:
        """Periods held by open holds on these clinicians overlapping the range."""
        ...
