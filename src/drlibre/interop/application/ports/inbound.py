from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from drlibre.interop.domain.filters import (
    AppointmentFilter,
    LocationFilter,
    LocationKind,
    Near,
    OrganizationFilter,
    OrganizationKind,
    Paging,
    PatientFilter,
    PractitionerFilter,
    RoleFilter,
    ScheduleFilter,
    ServiceFilter,
    SpecialtyFilter,
)
from drlibre.interop.domain.reader import Reader, ReaderKind
from drlibre.interop.domain.rows import (
    HELD,
    AppointmentKind,
    AppointmentRow,
    AvailabilityRow,
    DepartmentRow,
    HospitalRow,
    PatientRow,
    PractitionerRow,
    RoleRow,
    RoomRow,
    ScheduleRow,
    ServiceRow,
    SpecialtyRow,
    TimeOffRow,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

__all__ = [
    "HELD",
    "AppointmentFilter",
    "AppointmentKind",
    "AppointmentRow",
    "AvailabilityRow",
    "ConditionalWrites",
    "DepartmentRow",
    "DirectoryQueries",
    "HospitalRow",
    "InteropAppointmentQueries",
    "LocationFilter",
    "LocationKind",
    "Locked",
    "Near",
    "OrganizationFilter",
    "OrganizationKind",
    "Paging",
    "PatientFilter",
    "PatientQueries",
    "PatientRow",
    "PractitionerFilter",
    "PractitionerRow",
    "Reader",
    "ReaderKind",
    "Readers",
    "RoleFilter",
    "RoleRow",
    "RoomRow",
    "ScheduleFilter",
    "ScheduleRow",
    "ServiceFilter",
    "ServiceRow",
    "SpecialtyFilter",
    "SpecialtyRow",
    "StaleVersionError",
    "TimeOffRow",
    "WriteTarget",
]


class Readers(Protocol):
    def of(self, user_id: Id | None) -> Reader:
        """None is anonymous; a profile is a clinician, an active admin an admin, else patient."""
        ...


class DirectoryQueries(Protocol):
    """Reference data a reader may see; without paging, every match comes back on one page."""

    def organizations(
        self, criteria: OrganizationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | DepartmentRow]:
        """Hospitals and departments, active ones unless the admin reads them."""
        ...

    def locations(
        self, criteria: LocationFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[HospitalRow | RoomRow]:
        """Hospital sites and rooms, active ones unless the admin reads them."""
        ...

    def services(
        self, criteria: ServiceFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ServiceRow]:
        """Active types booked online; staff also see offline ones, the admin inactive ones."""
        ...

    def specialties(
        self, criteria: SpecialtyFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[SpecialtyRow]:
        """Specialties, active ones unless the admin reads them."""
        ...

    def practitioners(
        self, criteria: PractitionerFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PractitionerRow]:
        """Active clinicians; staff see every clinician, the admin also admins."""
        ...

    def roles(
        self, criteria: RoleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[RoleRow]:
        """Like practitioners; weight, time-off reasons and offline types for staff only."""
        ...

    def schedules(
        self, criteria: ScheduleFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[ScheduleRow]:
        """Rules of active clinicians; staff see every rule."""
        ...


class PatientQueries(Protocol):
    def patients(
        self, criteria: PatientFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[PatientRow]:
        """Patients the reader sees: self, a clinician's own patients, all for the admin."""
        ...

    def exists(self, patient_id: Id) -> bool:
        """Whether a patient has that id, whoever reads: hidden is not absent."""
        ...


class InteropAppointmentQueries(Protocol):
    def appointments(
        self, criteria: AppointmentFilter, reader: Reader, paging: Paging | None = None
    ) -> Page[AppointmentRow]:
        """By start: a patient's own and entries, a clinician's agenda and holds, all for admins."""
        ...

    def exists(self, appointment_id: Id) -> bool:
        """Whether an appointment, unbooked entry or open hold has that id, whoever reads."""
        ...


class Locked(StrEnum):
    """A row a conditional write locks, as the write it guards would lock it."""

    CLINICIAN = "clinician"
    USER = "user"
    APPOINTMENT = "appointment"
    AVAILABILITY_RULE = "availability_rule"


@dataclass(frozen=True, slots=True)
class WriteTarget:
    """The rows a write locks, in the product's lock order: clinician, patient, then the row."""

    rows: tuple[tuple[Locked, Id], ...]

    @classmethod
    def appointment(cls, *, clinician_id: Id, patient_id: Id, appointment_id: Id) -> "WriteTarget":
        return cls(
            (
                (Locked.CLINICIAN, clinician_id),
                (Locked.USER, patient_id),
                (Locked.APPOINTMENT, appointment_id),
            )
        )

    @classmethod
    def user(cls, *, user_id: Id) -> "WriteTarget":
        return cls(((Locked.USER, user_id),))

    @classmethod
    def clinician(cls, *, clinician_id: Id, row: tuple[Locked, Id] | None = None) -> "WriteTarget":
        """A clinician's profile, then the row of theirs a write changes, as `lock_profile`."""
        return cls(((Locked.CLINICIAN, clinician_id), *((row,) if row else ())))


class StaleVersionError(DomainError):
    """An If-Match naming a version the resource no longer has: `conflict`, answered 412."""

    def __init__(self) -> None:
        super().__init__(ErrorCode.CONFLICT, "Version périmée : relisez la ressource.")


class ConditionalWrites(Protocol):
    """If-Match under the write's own locks; none writes as is; a refusal keeps its commits."""

    def run[T](
        self,
        *,
        target: WriteTarget,
        expected: str | None,
        current: Callable[[], str],
        write: Callable[[], T],
    ) -> T:
        """Lock the target, refuse a stale `expected` with StaleVersionError, then write."""
        ...
