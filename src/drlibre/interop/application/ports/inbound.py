from typing import Protocol

from drlibre.interop.domain.filters import (
    LocationFilter,
    LocationKind,
    Near,
    OrganizationFilter,
    OrganizationKind,
    Paging,
    PractitionerFilter,
    RoleFilter,
    ScheduleFilter,
    ServiceFilter,
    SpecialtyFilter,
)
from drlibre.interop.domain.reader import Reader, ReaderKind
from drlibre.interop.domain.rows import (
    AvailabilityRow,
    DepartmentRow,
    HospitalRow,
    PractitionerRow,
    RoleRow,
    RoomRow,
    ScheduleRow,
    ServiceRow,
    SpecialtyRow,
    TimeOffRow,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

__all__ = [
    "AvailabilityRow",
    "DepartmentRow",
    "DirectoryQueries",
    "HospitalRow",
    "LocationFilter",
    "LocationKind",
    "Near",
    "OrganizationFilter",
    "OrganizationKind",
    "Paging",
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
    "TimeOffRow",
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
