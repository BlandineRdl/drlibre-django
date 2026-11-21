from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class BookableType:
    id: Id
    department_id: Id
    duration_minutes: int
    needs_room: bool
    bookable_online: bool
    active: bool


@dataclass(frozen=True, slots=True)
class BookableClinician:
    id: Id
    department_id: Id
    active: bool
    default_room_id: Id | None
    weight: int
    last_assigned_at: datetime | None


@dataclass(frozen=True, slots=True)
class Venue:
    """Where and with whom a clinician sees patients, as emails and pages name them."""

    hospital_name: str
    time_zone: str
    provider_name: str


@dataclass(frozen=True, slots=True)
class IssuedCode:
    code: str
    code_hash: str


@dataclass(frozen=True, slots=True)
class OpenedSession:
    token: str
    expires_at: datetime


class Appointments(Protocol):
    def add(self, appointment: Appointment) -> None:
        """Store the appointment."""
        ...

    def get(self, appointment_id: Id) -> Appointment | None:
        """The stored appointment, whatever its status."""
        ...

    def conflicting_resources(
        self, *, clinician_id: Id, patient_id: Id, start: datetime, end: datetime
    ) -> tuple[str, ...]:
        """Names ("clinician", "patient") having an active appointment overlapping the range."""
        ...

    def clinician_busy(self, clinician_id: Id, start: datetime, end: datetime) -> bool:
        """Whether the clinician has an active appointment overlapping the range."""
        ...

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        """Future active ONLINE or ROUND_ROBIN appointments of the patient."""
        ...

    def busy_rooms(self, room_ids: tuple[Id, ...], start: datetime, end: datetime) -> frozenset[Id]:
        """The given rooms used by an active appointment overlapping the range."""
        ...


class BookingDirectory(Protocol):
    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        """The type, active or not, or None when unknown."""
        ...

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        """The clinician profile, active or not, or None when unknown."""
        ...

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        """The department's active rooms in code order."""
        ...

    def venue(self, clinician_id: Id) -> Venue | None:
        """The clinician's hospital and name, or None when unknown."""
        ...


class FreeSlots(Protocol):
    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
    ) -> bool:
        """Whether the start is exactly one of the clinician's free slots for the type."""
        ...

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        """Active clinicians of the type's department with a free slot at the start."""
        ...


class SlotRefresh(Protocol):
    def refresh(self, clinician_id: Id) -> None:
        """Rebuild the clinician's stored slots, in the caller's unit of work."""
        ...


class ScheduleLocks(Protocol):
    def lock_clinician(self, clinician_id: Id) -> None:
        """Hold the clinician's writes until the caller's unit ends; unknown ids lock nothing."""
        ...

    def lock_patient(self, patient_id: Id) -> None:
        """Hold the patient's bookings until the caller's unit ends; unknown ids lock nothing."""
        ...

    def lock_rooms(self, department_id: Id) -> None:
        """Hold the department's rooms until the caller's unit ends; unknown ids lock none."""
        ...


class Patients(Protocol):
    def is_active(self, patient_id: Id) -> bool:
        """Whether the id is an active patient."""
        ...

    def email_of(self, patient_id: Id) -> str | None:
        """The patient's email, or None when the id is not a patient."""
        ...


class BookingNotices(Protocol):
    def code_sent(self, *, email: str, code: str) -> None:
        """Queue the verification code email, sent once the unit of work commits."""
        ...

    def confirmed(self, appointment: Appointment) -> None:
        """Queue the confirmation for the patient, sent once the unit of work commits."""
        ...


class RoundRobinLedger(Protocol):
    def record(self, clinician_id: Id, at: datetime) -> None:
        """Set the clinician's last round robin assignment, in the caller's unit of work."""
        ...


class Holds(Protocol):
    def add(self, hold: BookingHold) -> None:
        """Store the hold."""
        ...

    def get(self, hold_id: Id) -> BookingHold | None:
        """The hold, open or not, or None."""
        ...

    def open_for_email(self, email: str, at: datetime) -> BookingHold | None:
        """The email's hold still open at the instant, or None."""
        ...

    def held(
        self,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        *,
        at: datetime,
        excluding: Id | None,
    ) -> bool:
        """Whether a hold open at the instant, other than the excluded one, overlaps the range."""
        ...

    def open_in(
        self, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, *, at: datetime
    ) -> tuple[BookingHold, ...]:
        """Holds open at the instant on these clinicians and overlapping the range."""
        ...

    def expired(self, at: datetime) -> tuple[BookingHold, ...]:
        """Holds whose expiry is at or before the instant."""
        ...

    def delete(self, hold_id: Id) -> None:
        """Remove the hold; absent is a no-op."""
        ...


class VerificationCodes(Protocol):
    def put(self, code: VerificationCode) -> None:
        """Store the code, replacing the one of the same hold."""
        ...

    def for_hold(self, hold_id: Id) -> VerificationCode | None:
        """The hold's code, or None."""
        ...

    def for_hold_locked(self, hold_id: Id) -> VerificationCode | None:
        """The hold's code, held against other writers until the caller's unit ends."""
        ...

    def delete_for_hold(self, hold_id: Id) -> None:
        """Remove the hold's code; absent is a no-op."""
        ...


class CodeIssuer(Protocol):
    def issue(self) -> IssuedCode:
        """A fresh 6 digit code with its keyed hash."""
        ...

    def matches(self, code: str, code_hash: str) -> bool:
        """Whether the typed code hashes to the stored hash, in constant time."""
        ...


class PatientAccounts(Protocol):
    def provide(self, *, full_name: str, email: str, birth_date: date, phone: str | None) -> Id:
        """The patient of a proven email, created if unknown; forbidden for staff or inactive."""
        ...


class PatientSessions(Protocol):
    def open(self, *, patient_id: Id, user_agent: str) -> OpenedSession:
        """A 24 hour session, never extended, for the patient."""
        ...
