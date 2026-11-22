"""Helpers every FHIR router shares: rendering, reading ids and search tokens, parsing bodies."""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

import pydantic
from django.http import HttpRequest, HttpResponse

from drlibre.interfaces.fhir.bundle import entry, searchset
from drlibre.interfaces.fhir.outcome import fhir_response
from drlibre.interfaces.fhir.params import SearchQuery, reference_id, refuse_undeclared
from drlibre.interfaces.fhir.registry import ResourceRules
from drlibre.interfaces.fhir.schemas.bundle import BundleEntry
from drlibre.interfaces.fhir.schemas.common import FhirModel
from drlibre.interfaces.fhir.version import etag
from drlibre.interop.application.ports.inbound import Paging
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from drlibre.shared_kernel.validation import invalid_field

ACCEPTED_BODIES = frozenset({"application/fhir+json", "application/json"})
_BOOLEANS = {"true": True, "false": False}


def json_of(model: FhirModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def resource_response(model: FhirModel, version: str) -> HttpResponse:
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=200)
    response["ETag"] = etag(version)
    return response


def bundle_response(
    rules: ResourceRules, query: SearchQuery, total: int, entries: Sequence[BundleEntry]
) -> HttpResponse:
    bundle = searchset(resource_type=rules.type, query=query, total=total, entries=entries)
    return fhir_response(bundle.model_dump_json(by_alias=True, exclude_none=True), status=200)


def missing() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, "Ressource introuvable.")


def parse_id(raw: str) -> Id:
    """A resource id from the path; one that is not an id names nothing."""
    try:
        return Id.parse(raw)
    except ValueError as error:
        raise missing() from error


def read_one[T](request: HttpRequest, found: Page[T]) -> T:
    refuse_undeclared(request.GET, frozenset())
    if not found.items:
        raise missing()
    return found.items[0]


def paging_of(query: SearchQuery) -> Paging:
    return Paging(count=query.count, page=query.page, descending=query.sort[:1] == ("-name",))


def token(query: SearchQuery, name: str) -> str | None:
    raw = query.first(name)
    return raw.rpartition("|")[2] if raw is not None else None


def boolean(query: SearchQuery, name: str) -> bool | None:
    raw = token(query, name)
    if raw is None:
        return None
    if raw not in _BOOLEANS:
        raise invalid_field(name, "Saisissez true ou false.")
    return _BOOLEANS[raw]


def choice[T](query: SearchQuery, name: str, choices: dict[str, T]) -> T | None:
    raw = token(query, name)
    if raw is None:
        return None
    if raw not in choices:
        raise invalid_field(name, f"Valeur non prise en charge : {raw}.")
    return choices[raw]


def reference(query: SearchQuery, name: str, *types: str) -> Id | None:
    raw = query.first(name)
    if raw is None:
        return None
    found = reference_id(name, raw, *types)
    try:
        return Id.parse(found)
    except ValueError as error:
        raise invalid_field(name, f"Saisissez une référence {types[0]}/<id>.") from error


class _Identified(Protocol):
    @property
    def id(self) -> Id: ...


def entries_of[T: _Identified](
    rules: ResourceRules, rows: Sequence[T], build: Callable[[T], FhirModel], **include: bool
) -> list[BundleEntry]:
    return [entry(rules.type, str(r.id), json_of(build(r)), **include) for r in rows]


def require_fhir_json(request: HttpRequest) -> None:
    if request.content_type not in ACCEPTED_BODIES:
        raise DomainError(ErrorCode.INVALID_INPUT, "Envoyez le corps en application/fhir+json.")


def read_body[M: FhirModel](request: HttpRequest, model: type[M]) -> M:
    """The request body as the resource, after the caller is known; a bad one is invalid_input."""
    require_fhir_json(request)
    try:
        return model.model_validate_json(request.body)
    except pydantic.ValidationError as error:
        fields = [
            {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in error.errors()
        ]
        raise DomainError(
            ErrorCode.INVALID_INPUT, "Ressource invalide.", {"fields": fields}
        ) from error
