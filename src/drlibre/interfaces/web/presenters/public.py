from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlencode

from drlibre.interfaces.web.presenters.search import (
    OptionView,
    PaginationView,
    ResultView,
    SlotLinkView,
    provider_result,
)
from drlibre.interfaces.web.presenters.slots import (
    NO_AVAILABILITY,
    clinician_booking_url,
    day_label,
    first_available_url,
    local,
    slot_label,
)
from drlibre.search.application.ports.inbound import (
    DEFAULT_PAGE_SIZE,
    HospitalPage,
    ProviderWeek,
    SearchCriteria,
    SpecialtyPage,
)

NO_SLOT_THAT_DAY = "Aucun créneau"


@dataclass(frozen=True, slots=True)
class DayView:
    label: str
    slots: tuple[SlotLinkView, ...]
    empty_text: str
    past: bool = False


@dataclass(frozen=True, slots=True)
class ProviderPageView:
    name: str
    lines: tuple[str, ...]
    bio: str
    types: tuple[OptionView, ...]
    week_label: str
    previous_url: str
    next_url: str
    days: tuple[DayView, ...]
    zone_note: str
    week_value: str
    empty_week_text: str
    next_slot_text: str = ""
    next_slot_url: str = ""


def _provider_url(provider_id: object, type_id: object, week: date | None = None) -> str:
    query = {"type": str(type_id)}
    if week:
        query["week"] = week.isoformat()
    return f"/providers/{provider_id}?{urlencode(query)}"


def provider_page_view(page: ProviderWeek) -> ProviderPageView:
    detail, zone = page.detail, page.detail.time_zone
    by_day: dict[date, list[SlotLinkView]] = {page.monday + timedelta(days=n): [] for n in range(7)}
    for start in page.starts:
        at = local(start, zone)
        if at.date() in by_day:
            link = clinician_booking_url(page.type_id, detail.id, start)
            by_day[at.date()].append(SlotLinkView(f"{at:%H:%M}", link))
    past = page.today or page.monday
    days = tuple(
        DayView(day_label(day), tuple(slots), _empty_day(day < past, slots), day < past)
        for day, slots in by_day.items()
    )
    following = page.next_start and local(page.next_start, zone)
    sunday = page.monday + timedelta(days=6)
    return ProviderPageView(
        name=detail.full_name,
        lines=(
            f"{detail.title} · {detail.specialty_name}",
            f"{detail.hospital_name} · {detail.department_name} · {detail.city}",
        ),
        bio=detail.bio,
        types=tuple(
            OptionView(str(t.id), f"{t.name} {t.duration_minutes} min", t.id == page.type_id)
            for t in detail.types
        ),
        week_label=f"Semaine du {day_label(page.monday)} au {day_label(sunday)}",
        previous_url=(
            _provider_url(detail.id, page.type_id, page.previous_monday)
            if page.previous_monday
            else ""
        ),
        next_url=(
            _provider_url(detail.id, page.type_id, page.next_monday) if page.next_monday else ""
        ),
        days=days,
        zone_note=f"Heures de {zone}.",
        week_value=page.monday.isoformat(),
        empty_week_text="" if page.starts else "Aucun créneau libre cette semaine.",
        next_slot_text=f"Prochain créneau libre : {day_label(following.date())} à {following:%H:%M}"
        if following
        else "",
        next_slot_url=_provider_url(detail.id, page.type_id, following.date()) if following else "",
    )


def _empty_day(past: bool, slots: list[SlotLinkView]) -> str:
    if slots:
        return ""
    return "Passé" if past else NO_SLOT_THAT_DAY


@dataclass(frozen=True, slots=True)
class FirstByTypeView:
    label: str
    slot: SlotLinkView | None
    empty_text: str


@dataclass(frozen=True, slots=True)
class HospitalPageView:
    name: str
    address: str
    phone: str
    description: str
    departments: tuple[str, ...]
    specialties: tuple[str, ...]
    first_by_type: tuple[FirstByTypeView, ...]
    providers: tuple[ResultView, ...]
    zone_note: str


def hospital_page_view(page: HospitalPage) -> HospitalPageView:
    detail = page.detail
    zone = detail.time_zone
    firsts = tuple(
        FirstByTypeView(
            label=f"{t.type_name} {t.duration_minutes} min · {t.department_name}",
            slot=SlotLinkView(
                slot_label(t.start, zone), first_available_url(t.type_id, t.department_id, t.start)
            )
            if t.start
            else None,
            empty_text="" if t.start else NO_AVAILABILITY,
        )
        for t in page.first_by_type
    )
    return HospitalPageView(
        name=detail.name,
        address=f"{detail.street}, {detail.postal_code} {detail.city}, {detail.country}",
        phone=detail.phone,
        description=detail.description,
        departments=detail.departments,
        specialties=detail.specialties,
        first_by_type=firsts,
        providers=tuple(provider_result(p) for p in page.providers),
        zone_note=f"Heures de {zone}.",
    )


@dataclass(frozen=True, slots=True)
class SpecialtyPageView:
    name: str
    providers: tuple[ResultView, ...]
    pagination: PaginationView
    empty_text: str


def _specialty_url(specialty_id: object, criteria: SearchCriteria, page: int) -> str:
    query: dict[str, str] = {}
    if criteria.sort.value != "soonest":
        query["sort"] = criteria.sort.value
    if criteria.size != DEFAULT_PAGE_SIZE:
        query["size"] = str(criteria.size)
    if page > 1:
        query["page"] = str(page)
    base = f"/specialties/{specialty_id}"
    return f"{base}?{urlencode(query)}" if query else base


def specialty_page_view(page: SpecialtyPage, criteria: SearchCriteria) -> SpecialtyPageView:
    found = page.providers
    previous = (
        _specialty_url(page.detail.id, criteria, found.number - 1) if found.number > 1 else ""
    )
    following = (
        _specialty_url(page.detail.id, criteria, found.number + 1)
        if found.number < found.pages
        else ""
    )
    first = (found.number - 1) * found.size + 1
    summary = (
        f"{first} à {first + len(found.items) - 1} sur {found.total} praticien(s) · "
        f"page {found.number} sur {found.pages}"
        if found.items
        else "0 praticien"
    )
    return SpecialtyPageView(
        name=page.detail.name,
        providers=tuple(provider_result(p) for p in found.items),
        pagination=PaginationView(summary, previous, following, ()),
        empty_text="" if found.items else "Aucun praticien réservable pour cette spécialité.",
    )
