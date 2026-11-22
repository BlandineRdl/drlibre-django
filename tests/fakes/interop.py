import uuid
from collections.abc import Callable, Iterable, Iterator

from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import (
    HELD,
    AppointmentFilter,
    AppointmentKind,
    AppointmentResponseFilter,
    AppointmentResponseQueries,
    AppointmentResponseRow,
    AppointmentRow,
    AuditAction,
    AuditEventFilter,
    AuditEventQueries,
    AuditEventRow,
    CommunicationFilter,
    CommunicationQueries,
    CommunicationRow,
    ConditionalWrites,
    InteropAppointmentQueries,
    Paging,
    PatientFilter,
    PatientQueries,
    PatientRow,
    Reader,
    ReaderKind,
    StaleVersionError,
    WriteTarget,
)
from drlibre.interop.domain.reader import admin_only
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.fakes.audit_log import InMemoryAuditLog
from tests.fakes.booking import InMemoryAppointments, InMemoryHolds, InMemoryWaitlist
from tests.fakes.notifications import InMemoryNotifications
from tests.fakes.organisation import InMemoryClinicianProfiles
from tests.fakes.users import InMemoryUsers


class InMemoryPatientQueries(PatientQueries):
    def __init__(self, *, users: InMemoryUsers, appointments: Iterable[Appointment]) -> None:
        self._users = users
        self._appointments = appointments

    def _sees(self, reader: Reader, patient_id: Id) -> bool:
        if reader.kind is ReaderKind.PATIENT:
            return reader.user_id == patient_id
        if reader.kind is ReaderKind.CLINICIAN:
            return any(
                a.patient_id == patient_id and a.clinician_id == reader.profile_id
                for a in self._appointments
            )
        return reader.is_admin

    def patients(
        self, criteria: PatientFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PatientRow]:
        found = sorted(
            (
                PatientRow(
                    u.id, u.full_name, u.email.value, u.phone, u.birth_date, u.active, u.updated_at
                )
                for u in self._users.rows.values()
                if u.role is Role.PATIENT
                and self._sees(reader, u.id)
                and (not criteria.ids or u.id in criteria.ids)
                and (criteria.name is None or criteria.name.lower() in u.full_name.lower())
                and (criteria.email is None or criteria.email.lower() == u.email.value.lower())
                and (criteria.phone is None or criteria.phone == u.phone)
                and (criteria.birth_date is None or criteria.birth_date == u.birth_date)
            ),
            key=lambda r: (r.full_name, str(r.id)),
            reverse=bool(paging and paging.descending),
        )
        if paging is None:
            return Page(tuple(found), len(found), 1)
        window = found[paging.offset : paging.offset + paging.count]
        return Page(tuple(window), len(found), paging.page)

    def exists(self, patient_id: Id) -> bool:
        user = self._users.get(patient_id)
        return user is not None and user.role is Role.PATIENT


class InMemoryConditionalWrites(ConditionalWrites):
    """Compares the versions and writes; nothing to lock in memory."""

    def run[T](
        self,
        *,
        target: WriteTarget,
        expected: str | None,
        current: Callable[[], str],
        write: Callable[[], T],
        all_or_nothing: bool = False,
    ) -> T:
        if expected is not None and current() != expected:
            raise StaleVersionError
        return write()


class InMemoryInteropAppointmentQueries(InteropAppointmentQueries):
    """Appointments, unbooked entries and open holds of the fake repositories, stamped now."""

    def __init__(
        self,
        *,
        appointments: InMemoryAppointments,
        waitlist: InMemoryWaitlist,
        holds: InMemoryHolds,
        profiles: InMemoryClinicianProfiles,
        clock: Clock,
    ) -> None:
        self._appointments = appointments
        self._waitlist = waitlist
        self._holds = holds
        self._profiles = profiles
        self._clock = clock

    def _user(self, profile_id: Id | None) -> Id | None:
        profile = self._profiles.get(profile_id) if profile_id else None
        return profile.user_id if profile else None

    def _rows(self, reader: Reader) -> Iterator[AppointmentRow]:
        now = self._clock.now()
        for a in self._appointments.rows:
            notes = a.clinical_notes if a.clinician_id == reader.profile_id else None
            yield AppointmentRow(
                a.id, AppointmentKind.APPOINTMENT, a.status.value, a.patient_id, a.clinician_id,
                self._user(a.clinician_id), a.appointment_type_id, a.room_id, a.start, a.end,
                None, None, a.source.value, a.reason, a.cancellation_reason, notes, now,
            )  # fmt: skip
        offered = {a.id: a for a in self._appointments.rows}
        for w in self._waitlist.rows.values():
            if w.status is WaitlistStatus.BOOKED:
                continue
            slot = offered.get(w.offered_appointment_id) if w.offered_appointment_id else None
            slot = slot if w.status is WaitlistStatus.OFFERED else None
            clinician = slot.clinician_id if slot else w.clinician_id
            yield AppointmentRow(
                w.id, AppointmentKind.WAITLIST, w.status.value, w.patient_id, clinician,
                self._user(clinician), w.appointment_type_id, None,
                slot.start if slot else None, slot.end if slot else None,
                w.earliest, w.latest, None, None, None, None, now,
            )  # fmt: skip
        for h in self._holds.rows.values():
            if h.expires_at > now:
                yield AppointmentRow(
                    h.id, AppointmentKind.HOLD, HELD, None, h.clinician_id,
                    self._user(h.clinician_id), h.appointment_type_id, None, h.start, h.end,
                    None, None, h.source.value, h.details.reason, None, None, now,
                )  # fmt: skip

    @staticmethod
    def _sees(reader: Reader, row: AppointmentRow) -> bool:
        if reader.kind is ReaderKind.PATIENT:
            return row.kind is not AppointmentKind.HOLD and row.patient_id == reader.user_id
        if reader.kind is ReaderKind.CLINICIAN:
            return (
                row.kind is not AppointmentKind.WAITLIST and row.clinician_id == reader.profile_id
            )
        return reader.is_admin

    @staticmethod
    def _matches(c: AppointmentFilter, row: AppointmentRow) -> bool:
        return (
            (not c.ids or row.id in c.ids)
            and (c.patient is None or row.patient_id == c.patient)
            and (c.practitioner is None or row.practitioner_id == c.practitioner)
            and (c.room is None or row.room_id == c.room)
            and (c.appointment_type is None or row.appointment_type_id == c.appointment_type)
            and (not c.statuses or (row.kind.value, row.status) in c.statuses)
            and (c.start_from is None or (row.start is not None and row.start >= c.start_from))
            and (c.start_before is None or (row.start is not None and row.start < c.start_before))
        )

    def appointments(
        self, criteria: AppointmentFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AppointmentRow]:
        found = sorted(
            (r for r in self._rows(reader) if self._sees(reader, r) and self._matches(criteria, r)),
            key=lambda r: (r.start or r.earliest, str(r.id)),
            reverse=bool(paging and paging.descending),
        )
        if paging is None:
            return Page(tuple(found), len(found), 1)
        window = found[paging.offset : paging.offset + paging.count]
        return Page(tuple(window), len(found), paging.page)

    def exists(self, appointment_id: Id) -> bool:
        return any(r.id == appointment_id for r in self._rows(Reader.anonymous()))


class InMemoryAppointmentResponseQueries(AppointmentResponseQueries):
    """Booked entries of the fake waitlist, stamped now."""

    def __init__(self, *, waitlist: InMemoryWaitlist, clock: Clock) -> None:
        self._waitlist = waitlist
        self._clock = clock

    def _rows(self) -> list[AppointmentResponseRow]:
        now = self._clock.now()
        booked = (w for w in self._waitlist.rows.values() if w.status is WaitlistStatus.BOOKED)
        return [AppointmentResponseRow(w.id, w.patient_id, now) for w in booked]

    @staticmethod
    def _sees(reader: Reader, row: AppointmentResponseRow) -> bool:
        return reader.is_admin or (
            reader.kind is ReaderKind.PATIENT and row.patient_id == reader.user_id
        )

    def responses(
        self, criteria: AppointmentResponseFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AppointmentResponseRow]:
        found = sorted(
            (
                r
                for r in self._rows()
                if self._sees(reader, r)
                and (not criteria.ids or r.id in criteria.ids)
                and criteria.patient in (None, r.patient_id)
            ),
            key=lambda r: (r.updated_at, str(r.id)),
            reverse=bool(paging and paging.descending),
        )
        if paging is None:
            return Page(tuple(found), len(found), 1)
        window = found[paging.offset : paging.offset + paging.count]
        return Page(tuple(window), len(found), paging.page)

    def exists(self, response_id: Id) -> bool:
        return any(r.id == response_id for r in self._rows())


def _page[T](found: list[T], paging: Paging | None) -> Page[T]:
    if paging is None:
        return Page(tuple(found), len(found), 1)
    return Page(tuple(found[paging.offset : paging.offset + paging.count]), len(found), paging.page)


class InMemoryCommunicationQueries(CommunicationQueries):
    """Notifications of the fake store, stamped when last read or sent."""

    def __init__(self, *, notifications: InMemoryNotifications, users: InMemoryUsers) -> None:
        self._notifications = notifications
        self._users = users

    def _rows(self) -> Iterator[CommunicationRow]:
        for n in self._notifications.rows:
            user = self._users.get(n.recipient_id)
            yield CommunicationRow(
                n.id, n.recipient_id, user.role.value if user else None, n.kind.value, n.title,
                n.body, n.appointment_id, n.created_at, n.read_at, n.read_at or n.created_at,
            )  # fmt: skip

    def communications(
        self, criteria: CommunicationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[CommunicationRow]:
        c = criteria
        found = sorted(
            (
                r
                for r in self._rows()
                if reader.user_id is not None
                and r.recipient_id == reader.user_id
                and (not c.ids or r.id in c.ids)
                and c.recipient in (None, r.recipient_id)
                and c.category in (None, r.kind)
                and (c.sent_from is None or r.sent >= c.sent_from)
                and (c.sent_before is None or r.sent < c.sent_before)
            ),
            key=lambda r: (r.sent, str(r.id)),
            reverse=bool(paging and paging.descending),
        )
        return _page(found, paging)

    def exists(self, communication_id: Id) -> bool:
        return any(r.id == communication_id for r in self._rows())


class InMemoryAuditEventQueries(AuditEventQueries):
    """Entries of the fake audit log, each given an id from its position."""

    def __init__(self, *, log: InMemoryAuditLog, users: InMemoryUsers) -> None:
        self._log = log
        self._users = users

    def _role(self, user_id: Id | None) -> str | None:
        user = self._users.get(user_id) if user_id else None
        return user.role.value if user else None

    def _rows(self) -> Iterator[AuditEventRow]:
        entries = zip(self._log.entries, self._log.correlation_ids, strict=True)
        for index, (e, correlation) in enumerate(entries):
            target = self._role(e.entity_id) if e.entity_type == "user" else None
            yield AuditEventRow(
                Id(uuid.UUID(int=index + 1)), e.actor, self._role(e.actor), e.action,
                e.entity_type, e.entity_id, target, tuple(sorted(e.metadata)), e.at, correlation,
            )  # fmt: skip

    def events(
        self, criteria: AuditEventFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AuditEventRow]:
        admin_only(reader)
        c = criteria
        found = sorted(
            (
                r
                for r in self._rows()
                if (not c.ids or r.id in c.ids)
                and c.agent in (None, r.actor_id)
                and c.entity in (None, r.entity_id)
                and c.entity_type in (None, r.entity_type)
                and (not c.actions or AuditAction.of(r.action) in c.actions)
                and (c.at_from is None or r.at >= c.at_from)
                and (c.at_before is None or r.at < c.at_before)
            ),
            key=lambda r: (r.at, str(r.id)),
            reverse=bool(paging and paging.descending),
        )
        return _page(found, paging)
