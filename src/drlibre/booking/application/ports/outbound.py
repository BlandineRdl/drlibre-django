from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.booking_rules import ClinicianAction, PatientAction
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class BookableType:
    id: Id
    department_id: Id
    duration_minutes: int
    needs_room: bool
    bookable_online: bool
    active: bool
    time_zone: str


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
        """Store the appointment; an active overlap of its clinician or patient is a conflict."""
        ...

    def save(self, appointment: Appointment) -> None:
        """Replace the stored appointment; an absent id is refused as not found."""
        ...

    def get(self, appointment_id: Id) -> Appointment | None:
        """The stored appointment, whatever its status."""
        ...

    def booked_starting(self, after: datetime, until: datetime) -> tuple[Appointment, ...]:
        """BOOKED appointments starting after the first instant, up to the second, by start."""
        ...

    def cancelled_of_type(
        self, appointment_type_id: Id, *, after: datetime, earliest: datetime, latest: datetime
    ) -> tuple[Appointment, ...]:
        """CANCELLED appointments of the type starting after `after` inside the window, by start."""
        ...

    def conflicting_resources(
        self,
        *,
        clinician_id: Id,
        patient_id: Id,
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> tuple[str, ...]:
        """Names ("clinician", "patient") with another active appointment overlapping the range."""
        ...

    def clinician_busy(self, clinician_id: Id, start: datetime, end: datetime) -> bool:
        """Whether the clinician has an active appointment overlapping the range."""
        ...

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        """Future active ONLINE or ROUND_ROBIN appointments of the patient."""
        ...

    def busy_rooms(
        self,
        room_ids: tuple[Id, ...],
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> frozenset[Id]:
        """The given rooms used by an active appointment, other than the excluded one, in range."""
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

    def clinician_of_user(self, user_id: Id) -> Id | None:
        """The clinician profile id of the user, or None when the user holds none."""
        ...


class FreeSlots(Protocol):
    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
        ignoring_appointment: Id | None = None,
    ) -> bool:
        """Whether the start is one of the clinician's free slots, the ignored appointment freed."""
        ...

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        """Active clinicians of the type's department with a free slot at the start."""
        ...


class SlotRefresh(Protocol):
    def refresh(self, clinician_id: Id) -> None:
        """Rebuild the clinician's stored slots, in the caller's unit of work."""
        ...


class ScheduleLocks(Protocol):
    def lock_email(self, email: str) -> None:
        """Serialise the visitors of one email until the caller's unit ends; stores nothing."""
        ...

    def lock_clinician(self, clinician_id: Id) -> None:
        """Hold the clinician's writes until the caller's unit ends; unknown ids lock nothing."""
        ...

    def lock_clinicians(self, clinician_ids: tuple[Id, ...]) -> None:
        """Hold all the clinicians' writes in one fixed order; unknown ids lock nothing."""
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

    def email_domain_of(self, patient_id: Id) -> str | None:
        """The domain of the patient's email, or None when the id is no patient."""
        ...

    def email_of(self, patient_id: Id) -> str | None:
        """The patient's email, or None when the id is not a patient."""
        ...

    def active_patient_by_email(self, email: str) -> Id | None:
        """The active patient of the email, any case, or None."""
        ...


class Staff(Protocol):
    def is_admin(self, user_id: Id) -> bool:
        """Whether the id is an active admin."""
        ...


class BookingNotices(Protocol):
    def code_sent(self, *, email: str, code: str) -> None:
        """Queue the verification code email, sent once the unit of work commits."""
        ...

    def confirmed(self, appointment: Appointment) -> None:
        """Queue the confirmation for the patient, sent once the unit of work commits."""
        ...

    def booked(self, appointment: Appointment) -> None:
        """Write the patient's « RDV réservé » notification in the unit of work; no email."""
        ...

    def rescheduled(self, appointment: Appointment) -> None:
        """Write the patient's « RDV déplacé » notification and queue its email."""
        ...

    def cancelled(self, appointment: Appointment) -> None:
        """Write the patient's « RDV annulé » notification and queue its email."""
        ...

    def reminded(self, appointment: Appointment) -> bool:
        """Write the reminder and queue its email; False, doing nothing, when already reminded."""
        ...

    def already_reminded(self, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        """Those of the appointments whose reminder is already written."""
        ...

    def waitlist_offered(self, entry: WaitlistEntry, start: datetime, clinician_id: Id) -> None:
        """Write « Créneau proposé », linking no appointment, and queue its email."""
        ...

    def waitlist_booked(self, appointment: Appointment) -> None:
        """Write the « Créneau réservé » notification and queue its email."""
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


@dataclass(frozen=True, slots=True)
class AgendaFilter:
    """Optional narrowing of a patient's agenda; the range bounds the start, end excluded."""

    clinician_id: Id | None = None
    status: AppointmentStatus | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True, slots=True)
class AgendaEntry:
    """An appointment with whom, where and what, as the patient's lists show it."""

    appointment: Appointment
    clinician_name: str
    clinician_title: str
    specialty: str
    hospital_name: str
    hospital_address: str
    time_zone: str
    department: str
    room: str | None
    appointment_type: str
    bookable_online: bool
    allowed_actions: frozenset[PatientAction] = frozenset()


class PatientAgenda(Protocol):
    def entries(self, patient_id: Id, agenda_filter: AgendaFilter) -> tuple[AgendaEntry, ...]:
        """The patient's appointments matching the filter, by start, actions left empty."""
        ...


@dataclass(frozen=True, slots=True)
class ClinicianFilter:
    """Optional narrowing of a clinician's agenda; the range bounds the start, end excluded."""

    patient_id: Id | None = None
    status: AppointmentStatus | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True, slots=True)
class ClinicianEntry:
    """An appointment with the patient, type and room, as the clinician's agenda shows it."""

    appointment: Appointment
    patient_name: str
    patient_phone: str | None
    patient_birth_date: date | None
    appointment_type: str
    type_colour: str
    room: str | None
    actions: frozenset[ClinicianAction] = frozenset()


@dataclass(frozen=True, slots=True)
class ClinicianPatient:
    """A patient seen by the clinician, with their last and next visit."""

    patient_id: Id
    full_name: str
    phone: str | None
    last_visit: datetime | None
    next_visit: datetime | None


@dataclass(frozen=True, slots=True)
class RoomLabel:
    id: Id
    name: str


@dataclass(frozen=True, slots=True)
class RoomBooking:
    """A room in use; the patient is named only on the clinician's own appointments."""

    room_id: Id
    start: datetime
    end: datetime
    patient_name: str | None


@dataclass(frozen=True, slots=True)
class RoomsDay:
    rooms: tuple[RoomLabel, ...]
    bookings: tuple[RoomBooking, ...]


class ClinicianAgenda(Protocol):
    def entries(
        self, clinician_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        """The clinician's appointments matching the filter, by start, notes and actions empty."""
        ...

    def detail(self, appointment_id: Id) -> ClinicianEntry | None:
        """One appointment with its clinical notes, or None when unknown."""
        ...

    def patients(
        self, clinician_id: Id, request: PageRequest, now: datetime
    ) -> Page[ClinicianPatient]:
        """Patients with an appointment of the clinician, by name, searched on the name."""
        ...

    def room_day(self, clinician_id: Id, start: datetime, end: datetime) -> RoomsDay:
        """Active rooms of the clinician's department and their active appointments in range."""
        ...

    def next_free_slot(self, clinician_id: Id, after: datetime, now: datetime) -> datetime | None:
        """The clinician's earliest stored free slot from the instant on, any type, not held."""
        ...


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    actor_id: Id | None
    action: str
    at: datetime


class AppointmentHistory(Protocol):
    def entries_of(self, appointment_id: Id) -> tuple[HistoryEntry, ...]:
        """The appointment's audit entries, oldest first; empty when there is none."""
        ...


@dataclass(frozen=True, slots=True)
class ExpiringEntry:
    """A waitlist entry due for expiry, with the start of its offered appointment if any."""

    entry: WaitlistEntry
    offered_start: datetime | None


class Waitlist(Protocol):
    def add(self, entry: WaitlistEntry) -> None:
        """Store the new entry."""
        ...

    def save(self, entry: WaitlistEntry) -> None:
        """Replace the stored entry; not_found when absent, conflict when its offer is taken."""
        ...

    def get(self, entry_id: Id) -> WaitlistEntry | None:
        """The entry, whatever its status, or None."""
        ...

    def get_locked(self, entry_id: Id) -> WaitlistEntry | None:
        """The entry, held against other writers until the caller's unit ends, or None."""
        ...

    def candidates_locked(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        excluding_patient: Id,
    ) -> tuple[WaitlistEntry, ...]:
        """WAITING entries the slot matches, other patients only, locked as a set, by id."""
        ...

    def holds_offer(self, appointment_id: Id) -> bool:
        """Whether an OFFERED entry holds the appointment."""
        ...

    def expiring_locked(self, now: datetime) -> tuple[ExpiringEntry, ...]:
        """Locked WAITING entries past latest, OFFERED ones whose offer starts by now; by id."""
        ...


@dataclass(frozen=True, slots=True)
class AdminAppointmentFilter:
    """Optional narrowing of every hospital's appointments; dates are the hospital's local days."""

    start_date: date | None = None
    end_date: date | None = None
    department_id: Id | None = None
    clinician_id: Id | None = None
    status: AppointmentStatus | None = None
    source: Source | None = None

    @classmethod
    def from_query(
        cls,
        *,
        start: str | None = None,
        end: str | None = None,
        department: str | None = None,
        clinician: str | None = None,
        status: str | None = None,
        source: str | None = None,
    ) -> "AdminAppointmentFilter":
        """Each unusable value falls back to no filter."""
        return cls(
            start_date=_date_or_none(start),
            end_date=_date_or_none(end),
            department_id=_id_or_none(department),
            clinician_id=_id_or_none(clinician),
            status=AppointmentStatus(status) if status in set(AppointmentStatus) else None,
            source=Source(source) if source in set(Source) else None,
        )


def _date_or_none(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _id_or_none(raw: str | None) -> Id | None:
    try:
        return Id.parse(raw) if raw else None
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class AdminAppointmentRow:
    """An appointment with whom, where and what, in its hospital's time zone; never its notes."""

    appointment: Appointment
    patient_name: str
    clinician_name: str
    department: str
    appointment_type: str
    room: str | None
    hospital_name: str
    time_zone: str


@dataclass(frozen=True, slots=True)
class ExportRow:
    """An exported appointment: ids, UTC instants and codes only, never a name or free text."""

    id: Id
    start: datetime
    end: datetime
    status: AppointmentStatus
    source: Source
    patient_id: Id
    clinician_id: Id
    department_id: Id
    appointment_type_id: Id
    room_id: Id | None


class AdminAppointments(Protocol):
    def page(
        self, appointment_filter: AdminAppointmentFilter, request: PageRequest
    ) -> Page[AdminAppointmentRow]:
        """Every hospital's matching appointments, latest start first then id, with the total."""
        ...

    def all(self, appointment_filter: AdminAppointmentFilter) -> tuple[ExportRow, ...]:
        """Every matching appointment, in the page's order."""
        ...
