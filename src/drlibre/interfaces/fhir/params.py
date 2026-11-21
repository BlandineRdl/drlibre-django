import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from django.http import QueryDict

from drlibre.interfaces.fhir.registry import ResourceRules
from drlibre.shared_kernel.validation import invalid_field

DEFAULT_COUNT = 20
MAX_COUNT = 100
_PAGING = frozenset({"_count", "_page"})
_PREFIXED = re.compile(r"(eq|ge|gt|le|lt)?(.+)")


class Prefix(StrEnum):
    EQ = "eq"
    GE = "ge"
    GT = "gt"
    LE = "le"
    LT = "lt"


@dataclass(frozen=True, slots=True)
class DateBound:
    prefix: Prefix
    value: date | datetime


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """A search's declared parameters, in request order, with its paging, sort and includes."""

    params: tuple[tuple[str, str], ...]
    count: int
    page: int
    sort: tuple[str, ...]
    includes: tuple[str, ...]

    def values(self, name: str) -> tuple[str, ...]:
        return tuple(value for key, value in self.params if key == name)

    def first(self, name: str) -> str | None:
        return next(iter(self.values(name)), None)


def refuse_undeclared(query: QueryDict, allowed: frozenset[str]) -> None:
    """Refuse any parameter the server does not declare, rather than silently ignore it."""
    unknown = sorted(set(query) - allowed)
    if unknown:
        raise invalid_field(unknown[0], "Paramètre non pris en charge.")


def _integer(query: QueryDict, name: str, default: int) -> int:
    raw = query.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise invalid_field(name, "Saisissez un nombre entier supérieur ou égal à 1.")
    return value


def _listed(query: QueryDict, name: str, allowed: tuple[str, ...]) -> tuple[str, ...]:
    found = tuple(v for raw in query.getlist(name) for v in raw.split(",") if v)
    for value in found:
        if value not in allowed:
            raise invalid_field(name, f"Valeur non prise en charge : {value}.")
    return found


def search_query(query: QueryDict, rules: ResourceRules) -> SearchQuery:
    """Parse a search; _count above 100 is lowered to 100, below 1 or not a number refused."""
    controls = (
        _PAGING
        | ({"_sort"} if rules.sorts else set())
        | ({"_include"} if rules.includes else set())
    )
    refuse_undeclared(query, controls | {p.name for p in rules.search})
    sorts = tuple(s for name in rules.sorts for s in (name, f"-{name}"))
    return SearchQuery(
        params=tuple((k, v) for k in query if k not in controls for v in query.getlist(k)),
        count=min(_integer(query, "_count", DEFAULT_COUNT), MAX_COUNT),
        page=_integer(query, "_page", 1),
        sort=_listed(query, "_sort", sorts),
        includes=_listed(query, "_include", rules.includes),
    )


def date_bound(name: str, raw: str) -> DateBound:
    """A date parameter with its optional eq, ge, gt, le or lt prefix; a day or an instant."""
    found = _PREFIXED.fullmatch(raw.strip())
    prefix, text = (found[1] or "eq", found[2]) if found else ("eq", raw)
    try:
        value: date | datetime = (
            date.fromisoformat(text) if len(text) == 10 else datetime.fromisoformat(text)
        )
    except ValueError as error:
        raise invalid_field(
            name, "Saisissez une date AAAA-MM-JJ ou un instant ISO 8601."
        ) from error
    if isinstance(value, datetime) and value.tzinfo is None:
        raise invalid_field(name, "Précisez le fuseau de l'instant.")
    return DateBound(Prefix(prefix), value)


def reference_id(name: str, raw: str, resource_type: str) -> str:
    """The id a reference parameter names, as `Type/id` or a bare id."""
    kind, _, rest = raw.strip().rpartition("/")
    if (kind and kind != resource_type) or not rest:
        raise invalid_field(name, f"Saisissez une référence {resource_type}/<id>.")
    return rest
