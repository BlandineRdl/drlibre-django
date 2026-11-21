from collections.abc import Callable
from datetime import datetime, timedelta

from drlibre.booking.application.ports.inbound import AppointmentQueries, BookedPeriod
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookableClinician,
    BookableType,
    BookingDirectory,
    CodeIssuer,
    FreeSlots,
    Holds,
    IssuedCode,
    Patients,
    RoundRobinLedger,
    ScheduleLocks,
    SlotRefresh,
    Venue,
    VerificationCodes,
)
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.fakes.users import InMemoryUsers


class InMemoryAppointments(Appointments):
    def __init__(self) -> None:
        self.rows: list[Appointment] = []

    def add(self, appointment: Appointment) -> None:
        self.rows.append(appointment)

    def save(self, appointment: Appointment) -> None:
        index = next((i for i, a in enumerate(self.rows) if a.id == appointment.id), None)
        if index is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
        self.rows[index] = appointment

    def get(self, appointment_id: Id) -> Appointment | None:
        return next((a for a in self.rows if a.id == appointment_id), None)

    def conflicting_resources(
        self,
        *,
        clinician_id: Id,
        patient_id: Id,
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> tuple[str, ...]:
        overlapping = [
            a
            for a in self.rows
            if a.active and a.id != excluding and a.start < end and start < a.end
        ]
        resources = (
            ("clinician", any(a.clinician_id == clinician_id for a in overlapping)),
            ("patient", any(a.patient_id == patient_id for a in overlapping)),
        )
        return tuple(name for name, hit in resources if hit)

    def clinician_busy(self, clinician_id: Id, start: datetime, end: datetime) -> bool:
        return any(
            a.active and a.clinician_id == clinician_id and a.start < end and start < a.end
            for a in self.rows
        )

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        online = (Source.ONLINE, Source.ROUND_ROBIN)
        return sum(
            1
            for a in self.rows
            if a.patient_id == patient_id and a.active and a.source in online and a.start > now
        )

    def busy_rooms(
        self,
        room_ids: tuple[Id, ...],
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> frozenset[Id]:
        return frozenset(
            a.room_id
            for a in self.rows
            if a.active
            and a.id != excluding
            and a.room_id in room_ids
            and a.room_id is not None
            and a.start < end
            and start < a.end
        )


class FixedBookingDirectory(BookingDirectory):
    def __init__(self) -> None:
        self.types: dict[Id, BookableType] = {}
        self.clinicians: dict[Id, BookableClinician] = {}
        self.department_rooms: dict[Id, tuple[Id, ...]] = {}
        self.venues: dict[Id, Venue] = {}

    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        return self.types.get(appointment_type_id)

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        return self.clinicians.get(clinician_id)

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        return self.department_rooms.get(department_id, ())

    def venue(self, clinician_id: Id) -> Venue | None:
        return self.venues.get(clinician_id)


class InMemoryFreeSlots(FreeSlots):
    """Free slots as (clinician, type, start) rows, hidden while an open hold covers them."""

    def __init__(self, holds: "InMemoryHolds", clock: Clock) -> None:
        self.free: set[tuple[Id, Id, datetime]] = set()
        self.durations: dict[Id, timedelta] = {}
        self.buffers: dict[Id, timedelta] = {}
        self.holds = holds
        self.clock = clock

    def _held(
        self, clinician_id: Id, appointment_type_id: Id, start: datetime, ignoring: Id | None
    ) -> bool:
        now = self.clock.now()
        end = start + self.durations.get(appointment_type_id, timedelta(minutes=30))
        buffer = self.buffers.get(appointment_type_id, timedelta())
        return any(
            h.clinician_id == clinician_id
            and h.id != ignoring
            and h.is_open(now)
            and h.start < end
            and start < h.end + buffer
            for h in self.holds.rows.values()
        )

    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
    ) -> bool:
        listed = (clinician_id, appointment_type_id, start) in self.free
        return listed and not self._held(clinician_id, appointment_type_id, start, ignoring_hold)

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        return tuple(
            c
            for c, t, s in self.free
            if t == appointment_type_id
            and s == start
            and not self._held(c, appointment_type_id, start, None)
        )


class RecordingSlotRefresh(SlotRefresh):
    def __init__(self) -> None:
        self.refreshed: list[Id] = []

    def refresh(self, clinician_id: Id) -> None:
        self.refreshed.append(clinician_id)


class RecordingScheduleLocks(ScheduleLocks):
    def __init__(self) -> None:
        self.emails: list[str] = []
        self.clinicians: list[Id] = []
        self.patients: list[Id] = []
        self.departments: list[Id] = []

    def lock_email(self, email: str) -> None:
        self.emails.append(email)

    def lock_rooms(self, department_id: Id) -> None:
        self.departments.append(department_id)

    def lock_clinician(self, clinician_id: Id) -> None:
        self.clinicians.append(clinician_id)

    def lock_clinicians(self, clinician_ids: tuple[Id, ...]) -> None:
        self.clinicians.extend(sorted(clinician_ids, key=lambda c: c.value))

    def lock_patient(self, patient_id: Id) -> None:
        self.patients.append(patient_id)


class InMemoryPatients(Patients):
    """Patients are the active PATIENT users of the in-memory users."""

    def __init__(self, users: InMemoryUsers) -> None:
        self.users = users

    def is_active(self, patient_id: Id) -> bool:
        user = self.users.rows.get(patient_id)
        return user is not None and user.active and user.role is Role.PATIENT

    def email_domain_of(self, patient_id: Id) -> str | None:
        user = self.users.rows.get(patient_id)
        return user.email.domain if user is not None and user.role is Role.PATIENT else None

    def email_of(self, patient_id: Id) -> str | None:
        user = self.users.rows.get(patient_id)
        return user.email.value if user is not None and user.role is Role.PATIENT else None


class InMemoryRoundRobinLedger(RoundRobinLedger):
    def __init__(self) -> None:
        self.assigned: dict[Id, datetime] = {}

    def record(self, clinician_id: Id, at: datetime) -> None:
        self.assigned[clinician_id] = at


class InMemoryHolds(Holds):
    def __init__(self) -> None:
        self.rows: dict[Id, BookingHold] = {}

    def add(self, hold: BookingHold) -> None:
        self.rows[hold.id] = hold

    def get(self, hold_id: Id) -> BookingHold | None:
        return self.rows.get(hold_id)

    def open_for_email(self, email: str, at: datetime) -> BookingHold | None:
        return next((h for h in self.rows.values() if h.email == email and h.is_open(at)), None)

    def held(
        self,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        *,
        at: datetime,
        excluding: Id | None,
    ) -> bool:
        return any(
            h.clinician_id == clinician_id
            and h.id != excluding
            and h.is_open(at)
            and h.overlaps(start, end)
            for h in self.rows.values()
        )

    def open_in(
        self, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, *, at: datetime
    ) -> tuple[BookingHold, ...]:
        return tuple(
            h
            for h in self.rows.values()
            if h.clinician_id in clinician_ids and h.is_open(at) and h.overlaps(start, end)
        )

    def expired(self, at: datetime) -> tuple[BookingHold, ...]:
        return tuple(h for h in self.rows.values() if not h.is_open(at))

    def delete(self, hold_id: Id) -> None:
        self.rows.pop(hold_id, None)


class InMemoryVerificationCodes(VerificationCodes):
    def __init__(self) -> None:
        self.rows: dict[Id, VerificationCode] = {}

    def put(self, code: VerificationCode) -> None:
        self.rows[code.hold_id] = code

    def for_hold(self, hold_id: Id) -> VerificationCode | None:
        return self.rows.get(hold_id)

    def for_hold_locked(self, hold_id: Id) -> VerificationCode | None:
        return self.rows.get(hold_id)

    def delete_for_hold(self, hold_id: Id) -> None:
        self.rows.pop(hold_id, None)


class FixedCodeIssuer(CodeIssuer):
    """Issues the same code every time; the hash is the code itself."""

    def __init__(self, code: str = "123456") -> None:
        self.code = code

    def issue(self) -> IssuedCode:
        return IssuedCode(self.code, self.code)

    def matches(self, code: str, code_hash: str) -> bool:
        return code == code_hash


class InMemoryAppointmentQueries(AppointmentQueries):
    """Reads the in-memory appointments; `clinician_users` maps a profile to its user."""

    def __init__(self, appointments: InMemoryAppointments) -> None:
        self.appointments = appointments
        self.clinician_users: dict[Id, Id] = {}

    def periods_of(
        self, clinician_id: Id, *, start: datetime, end: datetime
    ) -> tuple[BookedPeriod, ...]:
        return tuple(
            BookedPeriod(a.start, a.end, a.status)
            for a in self.appointments.rows
            if a.clinician_id == clinician_id and a.start < end and start < a.end
        )

    def dependents_of_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.appointment_type_id == appointment_type_id)

    def dependents_of_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.room_id == room_id)

    def dependents_of_clinician(self, clinician_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.clinician_id == clinician_id)

    def active_upcoming_for_clinician_user(
        self, user_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        return self._of(
            lambda a: (
                self.clinician_users.get(a.clinician_id) == user_id and a.active and a.start > after
            )
        )

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        return self._of(
            lambda a: a.patient_id == user_id or self.clinician_users.get(a.clinician_id) == user_id
        )

    def _of(self, keep: Callable[[Appointment], bool]) -> tuple[Dependent, ...]:
        found = sorted((a for a in self.appointments.rows if keep(a)), key=lambda a: a.start)
        return tuple(Dependent("appointment", a.id, "Rendez-vous") for a in found)
