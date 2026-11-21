from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from drlibre.booking.application.ports.outbound import (
    AgendaEntry,
    AgendaFilter,
    ClinicianEntry,
    ClinicianFilter,
    ClinicianPatient,
    RoomBooking,
    RoomLabel,
)
from drlibre.booking.domain.appointment import (
    MAX_CANCELLATION_REASON,
    MAX_CLINICAL_NOTES,
    Appointment,
    AppointmentStatus,
)
from drlibre.booking.domain.booking_rules import BookingRule, ClinicianAction, PatientAction
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

__all__ = [
    "MAX_CANCELLATION_REASON",
    "MAX_CLINICAL_NOTES",
    "AgendaEntry",
    "AgendaFilter",
    "AgendaHour",
    "Appointment",
    "AppointmentFile",
    "AppointmentQueries",
    "AppointmentStatus",
    "BookAppointment",
    "BookForPatient",
    "BookedPeriod",
    "BookingRule",
    "CancelAppointment",
    "CheckInAppointment",
    "ClinicianAction",
    "ClinicianAppointment",
    "ClinicianDay",
    "ClinicianDayView",
    "ClinicianEntry",
    "ClinicianFilter",
    "ClinicianPatient",
    "ClinicianPatients",
    "ClinicianWeek",
    "ClinicianWeekView",
    "CompleteAppointment",
    "CreateHold",
    "DayCounts",
    "DepartmentRoomsDay",
    "ExpireHolds",
    "HeldPeriod",
    "HistoryActor",
    "HistoryLine",
    "HoldCreated",
    "HoldSummary",
    "ListClinicianAppointments",
    "ListPatientAppointments",
    "MarkNoShow",
    "OpenHolds",
    "PatientAction",
    "PatientAppointments",
    "RequirePatient",
    "RescheduleAppointment",
    "ResendCode",
    "RoomBooking",
    "RoomLabel",
    "RoomsDayView",
    "SendReminders",
    "VerifiedBooking",
    "VerifyHold",
    "ViewAppointment",
    "ViewHold",
    "WriteClinicalNotes",
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
    def execute(self, *, appointment_id: Id, actor_id: Id, reason: str) -> Appointment:
        """Cancel the actor's own appointment, patient or clinician; a refusal writes nothing."""
        ...


class RescheduleAppointment(Protocol):
    def execute(self, *, appointment_id: Id, actor_id: Id, start: datetime) -> Appointment:
        """Move the actor's own BOOKED appointment, patient or clinician; refusals write nothing."""
        ...


class BookForPatient(Protocol):
    def execute(
        self,
        *,
        actor_id: Id,
        patient_id: Id,
        appointment_type_id: Id,
        start: datetime,
        room_id: Id | None = None,
        clinician_id: Id | None = None,
    ) -> Appointment:
        """Book an active patient in the caller's own calendar as STAFF; refusals write nothing."""
        ...


class CheckInAppointment(Protocol):
    def execute(self, *, actor_id: Id, appointment_id: Id) -> Appointment:
        """Mark the clinician's own BOOKED appointment arrived; notifies no one."""
        ...


class CompleteAppointment(Protocol):
    def execute(self, *, actor_id: Id, appointment_id: Id) -> Appointment:
        """Mark the clinician's own CHECKED_IN appointment completed; notifies no one."""
        ...


class MarkNoShow(Protocol):
    def execute(self, *, actor_id: Id, appointment_id: Id) -> Appointment:
        """Mark the clinician's own BOOKED appointment absent, freeing its slot; notifies no one."""
        ...


class WriteClinicalNotes(Protocol):
    def execute(self, *, actor_id: Id, appointment_id: Id, text: str) -> Appointment:
        """Store the clinician's notes on their own appointment; empty clears, too long refused."""
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


@dataclass(frozen=True, slots=True)
class PatientAppointments:
    """Upcoming soonest first, past latest first."""

    upcoming: tuple[AgendaEntry, ...]
    past: tuple[AgendaEntry, ...]


class ListPatientAppointments(Protocol):
    def execute(self, *, patient_id: Id, agenda_filter: AgendaFilter) -> PatientAppointments:
        """The patient's own appointments with their allowed actions; forbidden for staff."""
        ...


@dataclass(frozen=True, slots=True)
class DayCounts:
    """Cancelled appointments are counted apart, never among the appointments."""

    appointments: int
    cancelled: int
    completed: int
    no_show: int


@dataclass(frozen=True, slots=True)
class AgendaHour:
    """The appointments starting within one hour of the hospital's day."""

    hour: int
    entries: tuple[ClinicianEntry, ...]


@dataclass(frozen=True, slots=True)
class ClinicianDayView:
    day: date
    time_zone: str
    hours: tuple[AgendaHour, ...]
    counts: DayCounts
    next_free_slot: datetime | None


class ClinicianDay(Protocol):
    def execute(self, *, actor_id: Id, day: date | None) -> ClinicianDayView:
        """The clinician's own day in the hospital zone, today when none; forbidden without one."""
        ...


@dataclass(frozen=True, slots=True)
class ClinicianWeekView:
    monday: date
    time_zone: str
    entries: tuple[ClinicianEntry, ...]


class ClinicianWeek(Protocol):
    def execute(self, *, actor_id: Id, week: date | None) -> ClinicianWeekView:
        """The clinician's active appointments of the week holding the date, this week if none."""
        ...


class HistoryActor(StrEnum):
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"
    STAFF = "STAFF"


@dataclass(frozen=True, slots=True)
class HistoryLine:
    action: str
    actor: HistoryActor
    at: datetime


@dataclass(frozen=True, slots=True)
class AppointmentFile:
    """One appointment as its clinician sees it, notes, allowed actions and history included."""

    entry: ClinicianEntry
    time_zone: str
    patient_age: int | None
    history: tuple[HistoryLine, ...]


class ClinicianAppointment(Protocol):
    def execute(self, *, actor_id: Id, appointment_id: Id) -> AppointmentFile:
        """The clinician's own appointment; not_found when absent, forbidden for another's."""
        ...


class ClinicianPatients(Protocol):
    def execute(self, *, actor_id: Id, request: PageRequest) -> Page[ClinicianPatient]:
        """The clinician's own patients, searched by name, 20 per page."""
        ...


@dataclass(frozen=True, slots=True)
class RoomsDayView:
    day: date
    time_zone: str
    rooms: tuple[RoomLabel, ...]
    bookings: tuple[RoomBooking, ...]


class DepartmentRoomsDay(Protocol):
    def execute(self, *, actor_id: Id, day: date | None) -> RoomsDayView:
        """The day's occupancy of the clinician's department rooms, today when none."""
        ...


class ListClinicianAppointments(Protocol):
    def execute(
        self, *, actor_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        """The clinician's own appointments with their actions, by start, never their notes."""
        ...
