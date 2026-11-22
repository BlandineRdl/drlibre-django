from collections.abc import Callable, Iterable, Iterator

from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import (
    HELD,
    AppointmentFilter,
    AppointmentKind,
    AppointmentRow,
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
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.fakes.booking import InMemoryAppointments, InMemoryHolds, InMemoryWaitlist
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
