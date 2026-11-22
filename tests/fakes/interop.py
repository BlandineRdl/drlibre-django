from collections.abc import Callable, Iterable

from drlibre.booking.domain.appointment import Appointment
from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import (
    ConditionalWrites,
    Paging,
    PatientFilter,
    PatientQueries,
    PatientRow,
    Reader,
    ReaderKind,
    StaleVersionError,
    WriteTarget,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
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
