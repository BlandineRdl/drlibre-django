import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    AppointmentQueries,
    BookedPeriod,
    WaitlistOption,
    WaitlistQueries,
    WaitlistRow,
)
from drlibre.booking.application.ports.outbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    AdminAppointments,
    AgendaEntry,
    AgendaFilter,
    Appointments,
    BookableClinician,
    BookableType,
    BookingDirectory,
    CodeIssuer,
    ExpiringEntry,
    ExportRow,
    FreeSlots,
    Holds,
    IssuedCode,
    PatientAgenda,
    Patients,
    RoundRobinLedger,
    ScheduleLocks,
    SlotRefresh,
    Staff,
    Venue,
    VerificationCodes,
    Waitlist,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest
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

    def booked_starting(self, after: datetime, until: datetime) -> tuple[Appointment, ...]:
        found = (
            a
            for a in self.rows
            if a.status is AppointmentStatus.BOOKED and after < a.start <= until
        )
        return tuple(sorted(found, key=lambda a: (a.start, str(a.id))))

    def cancelled_of_type(
        self, appointment_type_id: Id, *, after: datetime, earliest: datetime, latest: datetime
    ) -> tuple[Appointment, ...]:
        found = (
            a
            for a in self.rows
            if a.status is AppointmentStatus.CANCELLED
            and a.appointment_type_id == appointment_type_id
            and a.start > after
            and earliest <= a.start
            and a.end <= latest
        )
        return tuple(sorted(found, key=lambda a: (a.start, str(a.id))))

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
        # Clinician profile of each user holding one.
        self.profiles_of_users: dict[Id, Id] = {}

    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        return self.types.get(appointment_type_id)

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        return self.clinicians.get(clinician_id)

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        return self.department_rooms.get(department_id, ())

    def venue(self, clinician_id: Id) -> Venue | None:
        return self.venues.get(clinician_id)

    def clinician_of_user(self, user_id: Id) -> Id | None:
        return self.profiles_of_users.get(user_id)


class InMemoryFreeSlots(FreeSlots):
    """Free slots as (clinician, type, start) rows, hidden while an open hold covers them."""

    def __init__(self, holds: "InMemoryHolds", clock: Clock) -> None:
        self.free: set[tuple[Id, Id, datetime]] = set()
        # Rows an appointment covers, free only while that appointment is ignored.
        self.behind: dict[tuple[Id, Id, datetime], Id] = {}
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
        ignoring_appointment: Id | None = None,
    ) -> bool:
        row = (clinician_id, appointment_type_id, start)
        listed = row in self.free or (
            ignoring_appointment is not None and self.behind.get(row) == ignoring_appointment
        )
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

    def active_patient_by_email(self, email: str) -> Id | None:
        wanted = email.strip().lower()
        found = (u for u in self.users.rows.values() if u.email.value == wanted)
        return next((u.id for u in found if u.active and u.role is Role.PATIENT), None)


class InMemoryStaff(Staff):
    """Admins are the active ADMIN users of the in-memory users."""

    def __init__(self, users: InMemoryUsers) -> None:
        self.users = users

    def is_admin(self, user_id: Id) -> bool:
        user = self.users.rows.get(user_id)
        return user is not None and user.active and user.role is Role.ADMIN


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


class InMemoryWaitlist(Waitlist):
    """Entries by id; offered starts read from the in-memory appointments."""

    def __init__(self, appointments: InMemoryAppointments) -> None:
        self.rows: dict[Id, WaitlistEntry] = {}
        self.appointments = appointments

    def add(self, entry: WaitlistEntry) -> None:
        self._refuse_taken_offer(entry)
        self.rows[entry.id] = entry

    def save(self, entry: WaitlistEntry) -> None:
        if entry.id not in self.rows:
            raise DomainError(ErrorCode.NOT_FOUND, "Entrée d'attente introuvable.")
        self._refuse_taken_offer(entry)
        self.rows[entry.id] = entry

    def get(self, entry_id: Id) -> WaitlistEntry | None:
        return self.rows.get(entry_id)

    def get_locked(self, entry_id: Id) -> WaitlistEntry | None:
        return self.rows.get(entry_id)

    def candidates_locked(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        excluding_patient: Id,
    ) -> tuple[WaitlistEntry, ...]:
        found = (
            e
            for e in self.rows.values()
            if e.status is WaitlistStatus.WAITING
            and e.patient_id != excluding_patient
            and e.matches(appointment_type_id, clinician_id, start, end)
        )
        return tuple(sorted(found, key=lambda e: e.id.value))

    def holds_offer(self, appointment_id: Id) -> bool:
        return any(self._offers(e, appointment_id) for e in self.rows.values())

    def expiring_locked(self, now: datetime) -> tuple[ExpiringEntry, ...]:
        due: list[ExpiringEntry] = []
        for entry in sorted(self.rows.values(), key=lambda e: e.id.value):
            offered = entry.offered_appointment_id
            appointment = self.appointments.get(offered) if offered else None
            start = appointment.start if appointment else None
            waiting_past = entry.status is WaitlistStatus.WAITING and entry.latest <= now
            offer_started = (
                entry.status is WaitlistStatus.OFFERED and start is not None and start <= now
            )
            if waiting_past or offer_started:
                due.append(ExpiringEntry(entry, start))
        return tuple(due)

    @staticmethod
    def _offers(entry: WaitlistEntry, appointment_id: Id) -> bool:
        return entry.status is WaitlistStatus.OFFERED and entry.offered_appointment_id == (
            appointment_id
        )

    def _refuse_taken_offer(self, entry: WaitlistEntry) -> None:
        offered = entry.offered_appointment_id
        if offered is None or entry.status is not WaitlistStatus.OFFERED:
            return
        if any(e.id != entry.id and self._offers(e, offered) for e in self.rows.values()):
            raise DomainError(
                ErrorCode.CONFLICT,
                "Ce créneau est déjà proposé à une autre entrée.",
                {"resources": ["waitlist_entry"]},
            )


class InMemoryAppointmentQueries(AppointmentQueries):
    """Reads in-memory appointments and waitlist; `clinician_users` maps a profile to its user."""

    def __init__(
        self, appointments: InMemoryAppointments, waitlist: InMemoryWaitlist | None = None
    ) -> None:
        self.appointments = appointments
        self.waitlist = waitlist or InMemoryWaitlist(appointments)
        self.clinician_users: dict[Id, Id] = {}

    def periods_of(
        self, clinician_id: Id, *, start: datetime, end: datetime
    ) -> tuple[BookedPeriod, ...]:
        return tuple(
            BookedPeriod(a.id, a.start, a.end, a.status)
            for a in self.appointments.rows
            if a.clinician_id == clinician_id and a.start < end and start < a.end
        )

    def dependents_of_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.appointment_type_id == appointment_type_id) + self._waiting(
            lambda e: e.appointment_type_id == appointment_type_id
        )

    def dependents_of_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.room_id == room_id)

    def dependents_of_clinician(self, clinician_id: Id) -> tuple[Dependent, ...]:
        return self._of(lambda a: a.clinician_id == clinician_id) + self._waiting(
            lambda e: e.clinician_id == clinician_id
        )

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
        ) + self._waiting(lambda e: e.patient_id == user_id)

    def _of(self, keep: Callable[[Appointment], bool]) -> tuple[Dependent, ...]:
        found = sorted((a for a in self.appointments.rows if keep(a)), key=lambda a: a.start)
        return tuple(Dependent("appointment", a.id, "Rendez-vous") for a in found)

    def _waiting(self, keep: Callable[[WaitlistEntry], bool]) -> tuple[Dependent, ...]:
        found = sorted(
            (e for e in self.waitlist.rows.values() if keep(e)),
            key=lambda e: (e.created_at, e.id.value),
        )
        return tuple(
            Dependent("waitlist_entry", e.id, f"Attente du {e.created_at:%d/%m/%Y}") for e in found
        )


@dataclass(frozen=True, slots=True)
class AgendaClinician:
    """What the agenda names about a clinician: who, and the hospital and department."""

    name: str = "Dr Martin"
    title: str = "Dr"
    specialty: str = "Cardiologie"
    hospital_name: str = "Hôpital Nord"
    hospital_address: str = "1 rue de la Paix, 59000 Lille"
    time_zone: str = "Europe/Paris"
    department: str = "Cardiologie"


class InMemoryPatientAgenda(PatientAgenda):
    """Joins in-memory appointments to `clinicians`, `labels` (types, rooms) and `offline_types`."""

    def __init__(self, appointments: InMemoryAppointments) -> None:
        self.appointments = appointments
        self.clinicians: dict[Id, AgendaClinician] = {}
        self.labels: dict[Id, str] = {}
        self.offline_types: set[Id] = set()

    def entries(self, patient_id: Id, agenda_filter: AgendaFilter) -> tuple[AgendaEntry, ...]:
        f = agenda_filter
        rows = sorted(
            (
                a
                for a in self.appointments.rows
                if a.patient_id == patient_id
                and f.clinician_id in (None, a.clinician_id)
                and f.status in (None, a.status)
                and (f.start is None or a.start >= f.start)
                and (f.end is None or a.start < f.end)
            ),
            key=lambda a: a.start,
        )
        return tuple(self._entry(a) for a in rows)

    def _entry(self, appointment: Appointment) -> AgendaEntry:
        who = self.clinicians.get(appointment.clinician_id, AgendaClinician())
        return AgendaEntry(
            # Like the SQL agenda, never the clinician's notes.
            appointment=dataclasses.replace(appointment, clinical_notes=None),
            clinician_name=who.name,
            clinician_title=who.title,
            specialty=who.specialty,
            hospital_name=who.hospital_name,
            hospital_address=who.hospital_address,
            time_zone=who.time_zone,
            department=who.department,
            room=self.labels.get(appointment.room_id) if appointment.room_id else None,
            appointment_type=self.labels.get(appointment.appointment_type_id, ""),
            bookable_online=appointment.appointment_type_id not in self.offline_types,
        )


@dataclass(frozen=True, slots=True)
class WaitlistType:
    """What the waitlist names about a type; `active` covers its hospital too."""

    name: str = "Consultation"
    hospital_name: str = "Hôpital Nord"
    time_zone: str = "Europe/Paris"
    bookable_online: bool = True
    active: bool = True


@dataclass(frozen=True, slots=True)
class WaitlistClinician:
    name: str = "Dr Martin"
    department: str = "Cardiologie"
    active: bool = True


class InMemoryWaitlistQueries(WaitlistQueries):
    """Joins in-memory entries to users, `types` and `clinicians`."""

    def __init__(self, waitlist: InMemoryWaitlist, users: InMemoryUsers) -> None:
        self.waitlist = waitlist
        self.users = users
        self.types: dict[Id, WaitlistType] = {}
        self.clinicians: dict[Id, WaitlistClinician] = {}

    def own_entries(self, patient_id: Id) -> tuple[WaitlistRow, ...]:
        mine = (e for e in self.waitlist.rows.values() if e.patient_id == patient_id)
        newest = sorted(mine, key=lambda e: (e.created_at, e.id.value), reverse=True)
        return tuple(self._row(e) for e in newest)

    def page(self, status: str, request: PageRequest) -> Page[WaitlistRow]:
        rows = sorted(self.waitlist.rows.values(), key=lambda e: (e.created_at, e.id.value))
        if status in set(WaitlistStatus):
            rows = [e for e in rows if e.status.value == status]
        window = rows[request.offset : request.offset + PAGE_SIZE]
        return Page(tuple(self._row(e) for e in window), len(rows), request.number)

    def type_options(self, *, online_only: bool) -> tuple[WaitlistOption, ...]:
        found = (
            WaitlistOption(i, f"{t.name} · {t.hospital_name}")
            for i, t in self.types.items()
            if t.active and (t.bookable_online or not online_only)
        )
        return tuple(sorted(found, key=lambda o: (o.label, o.id.value)))

    def clinician_options(self) -> tuple[WaitlistOption, ...]:
        found = (
            WaitlistOption(i, f"{c.name} · {c.department}")
            for i, c in self.clinicians.items()
            if c.active
        )
        return tuple(sorted(found, key=lambda o: (o.label, o.id.value)))

    def _row(self, entry: WaitlistEntry) -> WaitlistRow:
        kind = self.types.get(entry.appointment_type_id, WaitlistType())
        patient = self.users.rows.get(entry.patient_id)
        clinician = self.clinicians.get(entry.clinician_id) if entry.clinician_id else None
        offered = entry.offered_appointment_id
        appointment = self.waitlist.appointments.get(offered) if offered else None
        return WaitlistRow(
            entry=entry,
            patient_name=patient.full_name if patient else "",
            appointment_type=kind.name,
            hospital_name=kind.hospital_name,
            time_zone=kind.time_zone,
            clinician_name=clinician.name if clinician else None,
            offered_start=appointment.start if appointment else None,
        )


@dataclass(frozen=True, slots=True)
class AdminClinician:
    """What the admin list names about a clinician: who, and their department and hospital."""

    name: str = "Dr Martin"
    department_id: Id = dataclasses.field(default_factory=Id)
    department: str = "Cardiologie"
    hospital_name: str = "Hôpital Nord"
    time_zone: str = "Europe/Paris"


class InMemoryAdminAppointments(AdminAppointments):
    """Joins in-memory appointments to users, `clinicians` and `labels` (types, rooms)."""

    def __init__(self, appointments: InMemoryAppointments, users: InMemoryUsers) -> None:
        self.appointments = appointments
        self.users = users
        self.clinicians: dict[Id, AdminClinician] = {}
        self.labels: dict[Id, str] = {}

    def _who(self, appointment: Appointment) -> AdminClinician:
        return self.clinicians.get(appointment.clinician_id, AdminClinician())

    def _matching(self, f: AdminAppointmentFilter) -> list[Appointment]:
        def keeps(a: Appointment) -> bool:
            who = self._who(a)
            day = a.start.astimezone(ZoneInfo(who.time_zone)).date()
            return (
                (f.start_date is None or day >= f.start_date)
                and (f.end_date is None or day <= f.end_date)
                and f.department_id in (None, who.department_id)
                and f.clinician_id in (None, a.clinician_id)
                and f.status in (None, a.status)
                and f.source in (None, a.source)
            )

        found = sorted((a for a in self.appointments.rows if keeps(a)), key=lambda a: a.id.value)
        return sorted(found, key=lambda a: a.start, reverse=True)

    def page(
        self, appointment_filter: AdminAppointmentFilter, request: PageRequest
    ) -> Page[AdminAppointmentRow]:
        found = self._matching(appointment_filter)
        window = found[request.offset : request.offset + PAGE_SIZE]
        return Page(tuple(self._row(a) for a in window), len(found), request.number)

    def all(self, appointment_filter: AdminAppointmentFilter) -> tuple[ExportRow, ...]:
        return tuple(self._export(a) for a in self._matching(appointment_filter))

    def _row(self, appointment: Appointment) -> AdminAppointmentRow:
        who = self._who(appointment)
        patient = self.users.rows.get(appointment.patient_id)
        room = appointment.room_id
        return AdminAppointmentRow(
            appointment=dataclasses.replace(appointment, clinical_notes=None),
            patient_name=patient.full_name if patient else "",
            clinician_name=who.name,
            department=who.department,
            appointment_type=self.labels.get(appointment.appointment_type_id, ""),
            room=self.labels.get(room) if room else None,
            hospital_name=who.hospital_name,
            time_zone=who.time_zone,
        )

    def _export(self, a: Appointment) -> ExportRow:
        return ExportRow(
            id=a.id,
            start=a.start,
            end=a.end,
            status=a.status,
            source=a.source,
            patient_id=a.patient_id,
            clinician_id=a.clinician_id,
            department_id=self._who(a).department_id,
            appointment_type_id=a.appointment_type_id,
            room_id=a.room_id,
        )
