from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlencode

from drlibre.interfaces.web.presenters.slots import (
    NO_AVAILABILITY,
    clinician_booking_url,
    first_available_url,
    slot_label,
)
from drlibre.search.application.ports.inbound import (
    FilterOptions,
    FirstSlot,
    HospitalResult,
    Moment,
    Option,
    ProviderResult,
    ResultCounts,
    SearchCriteria,
    SearchPage,
    Sort,
    SpecialtyResult,
    Window,
)

DEFAULT_SIZE = 20
SIZES = (10, 20, 50)
WINDOW_LABELS = {
    Window.ANY: "Toutes",
    Window.TODAY: "Aujourd'hui",
    Window.DAYS_3: "Sous 3 jours",
    Window.DAYS_7: "Sous 7 jours",
}
MOMENT_LABELS = {
    Moment.ANY: "Toute la journée",
    Moment.MORNING: "Matin (avant 12:00)",
    Moment.AFTERNOON: "Après-midi (12:00 à 17:00)",
    Moment.EVENING: "Soir (après 17:00)",
}
SORT_LABELS = {
    Sort.SOONEST: "Disponibilité la plus proche",
    Sort.NAME_ASC: "Nom de A à Z",
    Sort.NAME_DESC: "Nom de Z à A",
    Sort.DISTANCE: "Distance la plus courte",
}


class Kind(StrEnum):
    PROVIDERS = "providers"
    HOSPITALS = "hospitals"
    SPECIALTIES = "specialties"


KIND_LABELS = {
    Kind.PROVIDERS: "Praticiens",
    Kind.HOSPITALS: "Hôpitaux",
    Kind.SPECIALTIES: "Spécialités",
}


def kind_of(raw: str | None) -> Kind:
    try:
        return Kind(raw) if raw else Kind.PROVIDERS
    except ValueError:
        return Kind.PROVIDERS


@dataclass(frozen=True, slots=True)
class SlotLinkView:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class ResultView:
    title: str
    url: str
    lines: tuple[str, ...]
    slots_heading: str
    slots: tuple[SlotLinkView, ...]
    empty_text: str
    all_times_url: str
    all_times_label: str


@dataclass(frozen=True, slots=True)
class TabView:
    label: str
    url: str
    current: bool


@dataclass(frozen=True, slots=True)
class OptionView:
    value: str
    label: str
    selected: bool


@dataclass(frozen=True, slots=True)
class SelectView:
    name: str
    label: str
    options: tuple[OptionView, ...]


@dataclass(frozen=True, slots=True)
class PaginationView:
    summary: str
    previous_url: str
    next_url: str
    sizes: tuple[OptionView, ...]


@dataclass(frozen=True, slots=True)
class SearchView:
    kind: str
    text: str
    city: str
    from_date: str
    latitude: str
    longitude: str
    tabs: tuple[TabView, ...]
    selects: tuple[SelectView, ...]
    sorts: tuple[OptionView, ...]
    results: tuple[ResultView, ...]
    empty_text: str
    pagination: PaginationView
    zone_note: str
    heading: str
    has_filters: bool


def search_url(criteria: SearchCriteria, kind: Kind, *, page: int | None = None) -> str:
    """The address holding every value of the search, defaults left out."""
    query: dict[str, str] = {}
    if kind is not Kind.PROVIDERS:
        query["list"] = kind.value
    if criteria.text:
        query["q"] = criteria.text
    for name, value in (
        ("specialty", criteria.specialty),
        ("hospital", criteria.hospital),
        ("type", criteria.appointment_type),
    ):
        if value:
            query[name] = str(value)
    if criteria.city:
        query["city"] = criteria.city
    if criteria.from_date:
        query["from"] = criteria.from_date.isoformat()
    if criteria.window is not Window.ANY:
        query["window"] = criteria.window.value
    if criteria.moment is not Moment.ANY:
        query["moment"] = criteria.moment.value
    if criteria.sort is not Sort.SOONEST:
        query["sort"] = criteria.sort.value
    if criteria.size != DEFAULT_SIZE:
        query["size"] = str(criteria.size)
    if criteria.location:
        query["lat"] = f"{criteria.location.latitude:g}"
        query["lon"] = f"{criteria.location.longitude:g}"
    if page and page > 1:
        query["page"] = str(page)
    return f"/?{urlencode(query)}" if query else "/"


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _distance(km: float | None) -> str:
    return f"à {km:.0f} km" if km is not None else ""


def _first_slot_view(
    first: FirstSlot | None, time_zone: str
) -> tuple[str, tuple[SlotLinkView, ...]]:
    if first is None:
        return "", ()
    link = SlotLinkView(
        slot_label(first.start, time_zone),
        first_available_url(first.type_id, first.department_id, first.start),
    )
    return first.type_name, (link,)


def provider_result(item: ProviderResult) -> ResultView:
    next_slots = item.next_slots
    slots = (
        tuple(
            SlotLinkView(
                slot_label(start, item.time_zone),
                clinician_booking_url(next_slots.type_id, item.id, start),
            )
            for start in next_slots.starts
        )
        if next_slots
        else ()
    )
    place = f"{item.hospital_name} · {item.department_name} · {item.city}"
    lines = (
        f"{item.title} · {item.specialty_name}",
        place,
        *((_distance(item.distance_km),) if item.distance_km is not None else ()),
        f"Heures de {item.time_zone}",
    )
    return ResultView(
        title=item.full_name,
        url=f"/providers/{item.id}",
        lines=lines,
        slots_heading=f"{next_slots.type_name} {next_slots.duration_minutes} min"
        if next_slots
        else "",
        slots=slots,
        empty_text="" if slots else NO_AVAILABILITY,
        all_times_url=f"/providers/{item.id}",
        all_times_label="Tous les horaires",
    )


def hospital_result(item: HospitalResult) -> ResultView:
    heading, slots = _first_slot_view(item.first_slot, item.time_zone)
    lines = (
        f"{item.street}, {item.postal_code} {item.city}",
        f"Spécialités : {', '.join(item.specialties)}",
        _plural(item.providers, "praticien réservable", "praticiens réservables"),
        *((_distance(item.distance_km),) if item.distance_km is not None else ()),
        f"Heures de {item.time_zone}",
    )
    if slots:
        lines += (
            _plural(
                item.providers_with_slots,
                "praticien avec un créneau libre",
                "praticiens avec un créneau libre",
            ),
        )
    return ResultView(
        title=item.name,
        url=f"/hospitals/{item.id}",
        lines=lines,
        slots_heading=heading,
        slots=slots,
        empty_text="" if slots else NO_AVAILABILITY,
        all_times_url=f"/hospitals/{item.id}",
        all_times_label="Voir l'hôpital",
    )


def specialty_result(item: SpecialtyResult) -> ResultView:
    zone = item.time_zone or ""
    heading, slots = _first_slot_view(item.first_slot, zone) if item.time_zone else ("", ())
    lines = (
        _plural(item.providers, "praticien", "praticiens"),
        _plural(item.hospitals, "hôpital", "hôpitaux"),
        *((f"Heures de {zone}",) if slots else ()),
    )
    return ResultView(
        title=item.name,
        url=f"/specialties/{item.id}",
        lines=lines,
        slots_heading=heading,
        slots=slots,
        empty_text="" if slots else NO_AVAILABILITY,
        all_times_url=f"/specialties/{item.id}",
        all_times_label="Voir les praticiens",
    )


def _select(
    name: str, label: str, options: tuple[Option, ...], chosen: str, blank: str
) -> SelectView:
    choices = [OptionView("", blank, chosen == "")]
    choices += [OptionView(str(o.id), o.label, str(o.id) == chosen) for o in options]
    return SelectView(name, label, tuple(choices))


def _enum_select[E: StrEnum](
    name: str, label: str, labels: Mapping[E, str], chosen: E
) -> SelectView:
    return SelectView(
        name, label, tuple(OptionView(m.value, text, m is chosen) for m, text in labels.items())
    )


def _summary(page: SearchPage[object], noun_one: str, noun_many: str) -> str:
    if page.total == 0:
        return f"0 {noun_many}"
    first = (page.number - 1) * page.size + 1
    last = first + len(page.items) - 1
    return (
        f"{first} à {last} sur {_plural(page.total, noun_one, noun_many)} · "
        f"page {page.number} sur {page.pages}"
    )


_NOUNS = {
    Kind.PROVIDERS: ("praticien", "praticiens"),
    Kind.HOSPITALS: ("hôpital", "hôpitaux"),
    Kind.SPECIALTIES: ("spécialité", "spécialités"),
}


def _tabs(criteria: SearchCriteria, kind: Kind, counts: ResultCounts) -> tuple[TabView, ...]:
    total_by_kind = {
        Kind.PROVIDERS: counts.providers,
        Kind.HOSPITALS: counts.hospitals,
        Kind.SPECIALTIES: counts.specialties,
    }
    return tuple(
        TabView(f"{KIND_LABELS[k]} ({total_by_kind[k]})", search_url(criteria, k), k is kind)
        for k in Kind
    )


def _sorts(criteria: SearchCriteria) -> tuple[OptionView, ...]:
    return tuple(
        OptionView(s.value, text, s is criteria.sort)
        for s, text in SORT_LABELS.items()
        if s is not Sort.DISTANCE or criteria.location
    )


def _selects(criteria: SearchCriteria, options: FilterOptions) -> tuple[SelectView, ...]:
    return (
        _select("specialty", "Spécialité", options.specialties, _id(criteria.specialty), "Toutes"),
        _select("hospital", "Hôpital", options.hospitals, _id(criteria.hospital), "Tous"),
        _select(
            "type", "Type de rendez-vous", options.types, _id(criteria.appointment_type), "Tous"
        ),
        _enum_select("window", "Fenêtre", WINDOW_LABELS, criteria.window),
        _enum_select("moment", "Moment de la journée", MOMENT_LABELS, criteria.moment),
    )


def search_view(
    *,
    criteria: SearchCriteria,
    kind: Kind,
    page: SearchPage[ProviderResult] | SearchPage[HospitalResult] | SearchPage[SpecialtyResult],
    counts: ResultCounts,
    options: FilterOptions,
) -> SearchView:
    results = tuple(_result_of(item) for item in page.items)
    shown = criteria.on_page(page.number)
    previous = search_url(shown, kind, page=page.number - 1) if page.number > 1 else ""
    following = search_url(shown, kind, page=page.number + 1) if page.number < page.pages else ""
    sizes = tuple(OptionView(str(n), str(n), n == criteria.size) for n in SIZES)
    noun = _NOUNS[kind]
    return SearchView(
        kind=kind.value,
        text=criteria.text,
        city=criteria.city,
        from_date=criteria.from_date.isoformat() if criteria.from_date else "",
        latitude=f"{criteria.location.latitude:g}" if criteria.location else "",
        longitude=f"{criteria.location.longitude:g}" if criteria.location else "",
        tabs=_tabs(criteria, kind, counts),
        selects=_selects(criteria, options),
        sorts=_sorts(criteria),
        results=results,
        empty_text="Aucun résultat pour cette recherche." if not results else "",
        pagination=PaginationView(_summary(page, *noun), previous, following, sizes),
        zone_note="Heures affichées dans le fuseau de chaque hôpital, nommé sur le résultat.",
        heading=KIND_LABELS[kind],
        has_filters=bool(
            criteria.specialty
            or criteria.hospital
            or criteria.city
            or criteria.appointment_type
            or criteria.has_time_filter
        ),
    )


def _id(value: object) -> str:
    return str(value) if value else ""


def _result_of(item: ProviderResult | HospitalResult | SpecialtyResult) -> ResultView:
    if isinstance(item, ProviderResult):
        return provider_result(item)
    if isinstance(item, HospitalResult):
        return hospital_result(item)
    return specialty_result(item)
