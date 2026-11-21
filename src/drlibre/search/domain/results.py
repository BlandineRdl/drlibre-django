from dataclasses import dataclass
from datetime import date, datetime

from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class NextSlots:
    """Free starts of one clinician for one appointment type, in the hospital's zone."""

    type_id: Id
    type_name: str
    duration_minutes: int
    starts: tuple[datetime, ...]


@dataclass(frozen=True, slots=True)
class FirstSlot:
    """Earliest free start among several clinicians of one department."""

    start: datetime
    type_id: Id
    type_name: str
    department_id: Id


@dataclass(frozen=True, slots=True)
class ProviderResult:
    id: Id
    full_name: str
    title: str
    specialty_name: str
    hospital_id: Id
    hospital_name: str
    department_name: str
    city: str
    time_zone: str
    next_slots: NextSlots | None
    distance_km: float | None


@dataclass(frozen=True, slots=True)
class HospitalResult:
    id: Id
    name: str
    street: str
    postal_code: str
    city: str
    time_zone: str
    specialties: tuple[str, ...]
    providers: int
    providers_with_slots: int
    first_slot: FirstSlot | None
    distance_km: float | None


@dataclass(frozen=True, slots=True)
class SpecialtyResult:
    id: Id
    name: str
    providers: int
    hospitals: int
    first_slot: FirstSlot | None
    time_zone: str | None
    distance_km: float | None


@dataclass(frozen=True, slots=True)
class Found[T]:
    """One page of an ordered result set and the size of the whole set."""

    items: tuple[T, ...]
    total: int


@dataclass(frozen=True, slots=True)
class SearchPage[T]:
    items: tuple[T, ...]
    total: int
    number: int
    pages: int
    size: int


@dataclass(frozen=True, slots=True)
class ResultCounts:
    providers: int
    hospitals: int
    specialties: int


@dataclass(frozen=True, slots=True)
class BookableType:
    id: Id
    name: str
    duration_minutes: int


@dataclass(frozen=True, slots=True)
class ProviderDetail:
    id: Id
    full_name: str
    title: str
    specialty_name: str
    bio: str
    hospital_id: Id
    hospital_name: str
    department_id: Id
    department_name: str
    city: str
    time_zone: str
    types: tuple[BookableType, ...]


@dataclass(frozen=True, slots=True)
class HospitalDetail:
    id: Id
    name: str
    street: str
    postal_code: str
    city: str
    country: str
    phone: str
    description: str
    time_zone: str
    departments: tuple[str, ...]
    specialties: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TypeFirstSlot:
    """First available start of one online type across its department's clinicians."""

    type_id: Id
    type_name: str
    duration_minutes: int
    department_id: Id
    department_name: str
    start: datetime | None


@dataclass(frozen=True, slots=True)
class SpecialtyDetail:
    id: Id
    name: str


@dataclass(frozen=True, slots=True)
class ProviderWeek:
    detail: ProviderDetail
    type_id: Id
    monday: date
    previous_monday: date | None
    next_monday: date | None
    starts: tuple[datetime, ...]


@dataclass(frozen=True, slots=True)
class HospitalPage:
    detail: HospitalDetail
    providers: tuple[ProviderResult, ...]
    first_by_type: tuple[TypeFirstSlot, ...]


@dataclass(frozen=True, slots=True)
class SpecialtyPage:
    detail: SpecialtyDetail
    providers: SearchPage[ProviderResult]


@dataclass(frozen=True, slots=True)
class Option:
    id: Id
    label: str


@dataclass(frozen=True, slots=True)
class FilterOptions:
    """What the visitor may filter on: active specialties, hospitals and online types."""

    specialties: tuple[Option, ...]
    hospitals: tuple[Option, ...]
    types: tuple[Option, ...]
