from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id

__all__ = [
    "Appointment",
    "AppointmentQueries",
    "AppointmentStatus",
    "BookAppointment",
    "BookedPeriod",
    "CancelAppointment",
    "CreateHold",
    "ExpireHolds",
    "HeldPeriod",
    "HoldCreated",
    "HoldSummary",
    "OpenHolds",
    "RequirePatient",
    "RescheduleAppointment",
    "ResendCode",
    "SendReminders",
    "VerifiedBooking",
    "VerifyHold",
    "ViewAppointment",
    "ViewHold",
]


class RequirePatient(Protocol):
    def execute(self, *, user_id: Id) -> None:
        """Let an active patient through; staff, inactive or unknown users get forbidden."""
        ...


class BookAppointment(Protocol):
    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        """Book for the signed-in patient, any clinician if none named; refused writes nothing."""
        ...


class CancelAppointment(Protocol):
    def execute(self, *, appointment_id: Id, patient_id: Id, reason: str) -> Appointment:
        """Cancel the patient's own appointment for a reason; a refusal writes or sends nothing."""
        ...


class RescheduleAppointment(Protocol):
    def execute(self, *, appointment_id: Id, patient_id: Id, start: datetime) -> Appointment:
        """Move the patient's own BOOKED appointment, end recomputed; a refusal writes nothing."""
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
        """Hold the slot 10 minutes and email a code; refused on bad input, conflict or limits."""
        ...


@dataclass(frozen=True, slots=True)
class VerifiedBooking:
    """The outcome of a correct code: a session always, then the appointment or why not."""

    token: str
    expires_at: datetime
    outcome: Appointment | DomainError


class VerifyHold(Protocol):
    def execute(self, *, hold_id: Id, code: str, user_agent: str) -> VerifiedBooking:
        """Book on the right code, else refused; a placement refusal is returned, account kept."""
        ...


class ResendCode(Protocol):
    def execute(self, *, hold_id: Id, network: str) -> None:
        """Send a new code voiding the old, expiry unchanged; refused if unknown or over limits."""
        ...


class ExpireHolds(Protocol):
    def execute(self) -> int:
        """Delete expired holds and their codes, auditing each; returns how many."""
        ...


class SendReminders(Protocol):
    def execute(self) -> int:
        """Remind each BOOKED appointment of the next 24 hours once, auditing the count if any."""
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


@dataclass(frozen=True, slots=True)
class BookedPeriod:
    id: Id
    start: datetime
    end: datetime
    status: AppointmentStatus


class AppointmentQueries(Protocol):
    def periods_of(
        self, clinician_id: Id, *, start: datetime, end: datetime
    ) -> tuple[BookedPeriod, ...]:
        """The clinician's appointments overlapping the range, whatever their status."""
        ...

    def dependents_of_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        """Appointments of the type, labelled by their start, never a person."""
        ...

    def dependents_of_room(self, room_id: Id) -> tuple[Dependent, ...]:
        """Appointments held in the room, labelled by their start, never a person."""
        ...

    def dependents_of_clinician(self, clinician_id: Id) -> tuple[Dependent, ...]:
        """Appointments of the clinician profile, labelled by their start, never a person."""
        ...

    def active_upcoming_for_clinician_user(
        self, user_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        """Active appointments starting after the instant of the clinician holding this user."""
        ...

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        """Appointments where the user is the patient, or the clinician through their profile."""
        ...


@dataclass(frozen=True, slots=True)
class HoldSummary:
    """What a booking hold shows its visitor: the slot and the provider, never the details."""

    hold_id: Id
    clinician_id: Id
    appointment_type_id: Id
    start: datetime
    end: datetime
    expires_at: datetime
    open: bool
    first_available: bool


class ViewHold(Protocol):
    def execute(self, *, hold_id: Id) -> HoldSummary:
        """The hold's slot, open or just expired; not_found once it is gone."""
        ...


class ViewAppointment(Protocol):
    def execute(self, *, appointment_id: Id, patient_id: Id) -> Appointment:
        """The patient's own appointment; not_found when absent, forbidden for another patient."""
        ...
