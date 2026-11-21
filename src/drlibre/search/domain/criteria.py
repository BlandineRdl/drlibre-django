import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from drlibre.shared_kernel.ids import Id

PAGE_SIZES = (10, 20, 50)
DEFAULT_PAGE_SIZE = 20
MAX_TEXT = 100


class Window(StrEnum):
    ANY = "any"
    TODAY = "today"
    DAYS_3 = "3d"
    DAYS_7 = "7d"


class Moment(StrEnum):
    ANY = "any"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class Sort(StrEnum):
    SOONEST = "soonest"
    NAME_ASC = "name"
    NAME_DESC = "name-desc"
    DISTANCE = "distance"


@dataclass(frozen=True, slots=True)
class Location:
    latitude: float
    longitude: float


def _choice[E: StrEnum](kind: type[E], raw: str | None, default: E) -> E:
    try:
        return kind(raw) if raw else default
    except ValueError:
        return default


def _id(raw: str | None) -> Id | None:
    try:
        return Id.parse(raw) if raw else None
    except ValueError:
        return None


def _day(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _number(raw: str | None, low: float, high: float) -> float | None:
    try:
        value = float(raw) if raw else None
    except ValueError:
        return None
    return value if value is not None and math.isfinite(value) and low <= value <= high else None


def _page(raw: str | None) -> int:
    return int(raw) if raw and raw.isascii() and raw.isdigit() and int(raw) >= 1 else 1


def _size(raw: str | None) -> int:
    return int(raw) if raw and raw.isascii() and raw.isdigit() and int(raw) in PAGE_SIZES else 20


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    text: str = ""
    specialty: Id | None = None
    hospital: Id | None = None
    city: str = ""
    appointment_type: Id | None = None
    from_date: date | None = None
    window: Window = Window.ANY
    moment: Moment = Moment.ANY
    sort: Sort = Sort.SOONEST
    page: int = 1
    size: int = DEFAULT_PAGE_SIZE
    location: Location | None = None

    @classmethod
    def parse(cls, raw: Mapping[str, str]) -> "SearchCriteria":
        """Read the address values; each unusable one falls back to its default."""
        latitude, longitude = _number(raw.get("lat"), -90, 90), _number(raw.get("lon"), -180, 180)
        location = (
            Location(latitude, longitude)
            if latitude is not None and longitude is not None
            else None
        )
        sort = _choice(Sort, raw.get("sort"), Sort.SOONEST)
        return cls(
            text=raw.get("q", "").strip()[:MAX_TEXT],
            specialty=_id(raw.get("specialty")),
            hospital=_id(raw.get("hospital")),
            city=raw.get("city", "").strip()[:MAX_TEXT],
            appointment_type=_id(raw.get("type")),
            from_date=_day(raw.get("from")),
            window=_choice(Window, raw.get("window"), Window.ANY),
            moment=_choice(Moment, raw.get("moment"), Moment.ANY),
            sort=Sort.SOONEST if sort is Sort.DISTANCE and location is None else sort,
            page=_page(raw.get("page")),
            size=_size(raw.get("size")),
            location=location,
        )

    @property
    def has_time_filter(self) -> bool:
        return (
            self.from_date is not None
            or self.window is not Window.ANY
            or self.moment is not Moment.ANY
        )

    def on_page(self, page: int, size: int | None = None) -> "SearchCriteria":
        return replace(self, page=page, size=size or self.size)
