from dataclasses import dataclass
from enum import StrEnum


class Interaction(StrEnum):
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    SEARCH = "search-type"


class ParamType(StrEnum):
    TOKEN = "token"  # noqa: S105  # nosec B105
    STRING = "string"
    DATE = "date"
    REFERENCE = "reference"
    NUMBER = "number"
    SPECIAL = "special"


# Method and path, relative to /fhir, that serve each interaction.
_ROUTES = {
    Interaction.READ: ("GET", "/{type}/{id}"),
    Interaction.UPDATE: ("PUT", "/{type}/{id}"),
    Interaction.DELETE: ("DELETE", "/{type}/{id}"),
    Interaction.CREATE: ("POST", "/{type}"),
    Interaction.SEARCH: ("GET", "/{type}"),
}
WRITES = frozenset({Interaction.UPDATE, Interaction.DELETE, Interaction.CREATE})
SYSTEM_ROUTES = frozenset({("GET", "/metadata")})


@dataclass(frozen=True, slots=True)
class SearchParam:
    name: str
    type: ParamType


@dataclass(frozen=True, slots=True)
class ResourceRules:
    """What the server serves for one resource type; metadata, params and 405 all read it."""

    type: str
    interactions: tuple[Interaction, ...]
    search: tuple[SearchParam, ...] = ()
    includes: tuple[str, ...] = ()
    sorts: tuple[str, ...] = ()

    def routes(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            (method, path.replace("{type}", self.type))
            for method, path in (_ROUTES[i] for i in self.interactions)
        )

    def param(self, name: str) -> SearchParam | None:
        return next((p for p in self.search if p.name == name), None)


_REGISTRY: dict[str, ResourceRules] = {}


def declare(rules: ResourceRules) -> ResourceRules:
    """Register a resource once, at import of the module serving it."""
    if rules.type in _REGISTRY:
        raise ValueError(f"FHIR resource {rules.type} declared twice")
    _REGISTRY[rules.type] = rules
    return rules


def declared() -> tuple[ResourceRules, ...]:
    return tuple(_REGISTRY[name] for name in sorted(_REGISTRY))


def declared_routes() -> frozenset[tuple[str, str]]:
    return SYSTEM_ROUTES.union(*(rules.routes() for rules in declared()))
