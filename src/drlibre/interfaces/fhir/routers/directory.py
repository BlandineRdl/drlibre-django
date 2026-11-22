import uuid
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import reader
from drlibre.interfaces.fhir.bundle import entry, searchset
from drlibre.interfaces.fhir.mappers import directory as to
from drlibre.interfaces.fhir.outcome import fhir_response
from drlibre.interfaces.fhir.params import (
    Prefix,
    SearchQuery,
    date_bound,
    reference_id,
    refuse_undeclared,
    search_query,
)
from drlibre.interfaces.fhir.registry import (
    Interaction,
    ParamType,
    ResourceRules,
    SearchParam,
    declare,
)
from drlibre.interfaces.fhir.schemas.bundle import BundleEntry
from drlibre.interfaces.fhir.schemas.common import FhirModel
from drlibre.interfaces.fhir.version import etag
from drlibre.interop.application.ports.inbound import (
    DirectoryQueries,
    LocationFilter,
    LocationKind,
    Near,
    OrganizationFilter,
    OrganizationKind,
    Paging,
    PractitionerFilter,
    PractitionerRow,
    Reader,
    RoleFilter,
    RoleRow,
    ScheduleFilter,
    ServiceFilter,
    SpecialtyFilter,
    SpecialtyRow,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["directory"])

_READ_SEARCH = (Interaction.READ, Interaction.SEARCH)
_STRING, _TOKEN, _REFERENCE = ParamType.STRING, ParamType.TOKEN, ParamType.REFERENCE
_DATE = ParamType.DATE

ORGANIZATION = declare(
    ResourceRules(
        type="Organization",
        interactions=_READ_SEARCH,
        search=(
            SearchParam("name", _STRING),
            SearchParam("type", _TOKEN),
            SearchParam("partof", _REFERENCE),
            SearchParam("address-city", _STRING),
            SearchParam("active", _TOKEN),
        ),
        sorts=("name",),
    )
)
LOCATION = declare(
    ResourceRules(
        type="Location",
        interactions=_READ_SEARCH,
        search=(
            SearchParam("name", _STRING),
            SearchParam("address-city", _STRING),
            SearchParam("organization", _REFERENCE),
            SearchParam("partof", _REFERENCE),
            SearchParam("type", _TOKEN),
            SearchParam("near", ParamType.SPECIAL),
        ),
        sorts=("name",),
    )
)
HEALTHCARE_SERVICE = declare(
    ResourceRules(
        type="HealthcareService",
        interactions=_READ_SEARCH,
        search=(
            SearchParam("name", _STRING),
            SearchParam("organization", _REFERENCE),
            SearchParam("specialty", _TOKEN),
            SearchParam("active", _TOKEN),
        ),
        sorts=("name",),
    )
)
CODE_SYSTEM = declare(
    ResourceRules(
        type="CodeSystem",
        interactions=_READ_SEARCH,
        search=(SearchParam("name", _STRING), SearchParam("status", _TOKEN)),
    )
)
VALUE_SET = declare(ResourceRules(type="ValueSet", interactions=_READ_SEARCH))
PRACTITIONER = declare(
    ResourceRules(
        type="Practitioner",
        interactions=_READ_SEARCH,
        search=(SearchParam("name", _STRING), SearchParam("active", _TOKEN)),
        sorts=("name",),
    )
)
PRACTITIONER_ROLE = declare(
    ResourceRules(
        type="PractitionerRole",
        interactions=_READ_SEARCH,
        search=(
            SearchParam("practitioner", _REFERENCE),
            SearchParam("organization", _REFERENCE),
            SearchParam("specialty", _TOKEN),
            SearchParam("location", _REFERENCE),
            SearchParam("service", _REFERENCE),
            SearchParam("active", _TOKEN),
        ),
        includes=("PractitionerRole:practitioner", "PractitionerRole:organization"),
    )
)
SCHEDULE = declare(
    ResourceRules(
        type="Schedule",
        interactions=_READ_SEARCH,
        search=(
            SearchParam("actor", _REFERENCE),
            SearchParam("date", _DATE),
            SearchParam("active", _TOKEN),
        ),
    )
)

_NOWHERE = Id(uuid.UUID(int=0))
_BOOLEANS = {"true": True, "false": False}


def _queries() -> DirectoryQueries:
    return container().directory_queries


def _json(model: FhirModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def _resource(model: FhirModel, version: str) -> HttpResponse:
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=200)
    response["ETag"] = etag(version)
    return response


def _bundle(
    rules: ResourceRules, query: SearchQuery, total: int, entries: Sequence[BundleEntry]
) -> HttpResponse:
    bundle = searchset(resource_type=rules.type, query=query, total=total, entries=entries)
    return fhir_response(bundle.model_dump_json(by_alias=True, exclude_none=True), status=200)


def _missing() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, "Ressource introuvable.")


def _id(raw: str) -> Id:
    try:
        return Id.parse(raw)
    except ValueError as error:
        raise _missing() from error


def _read[T](request: HttpRequest, found: Page[T]) -> T:
    refuse_undeclared(request.GET, frozenset())
    if not found.items:
        raise _missing()
    return found.items[0]


def _paging(query: SearchQuery) -> Paging:
    return Paging(count=query.count, page=query.page, descending=query.sort[:1] == ("-name",))


def _token(query: SearchQuery, name: str) -> str | None:
    raw = query.first(name)
    return raw.rpartition("|")[2] if raw is not None else None


def _boolean(query: SearchQuery, name: str) -> bool | None:
    raw = _token(query, name)
    if raw is None:
        return None
    if raw not in _BOOLEANS:
        raise invalid_field(name, "Saisissez true ou false.")
    return _BOOLEANS[raw]


def _choice[T](query: SearchQuery, name: str, choices: dict[str, T]) -> T | None:
    raw = _token(query, name)
    if raw is None:
        return None
    if raw not in choices:
        raise invalid_field(name, f"Valeur non prise en charge : {raw}.")
    return choices[raw]


def _ref(query: SearchQuery, name: str, *types: str) -> Id | None:
    raw = query.first(name)
    if raw is None:
        return None
    found = reference_id(name, raw, *types)
    try:
        return Id.parse(found)
    except ValueError as error:
        raise invalid_field(name, f"Saisissez une référence {types[0]}/<id>.") from error


def _specialty_id(query: SearchQuery, known: dict[Id, SpecialtyRow]) -> Id | None:
    """A specialty token, by its code or id; an unknown one matches nothing."""
    raw = query.first("specialty")
    if raw is None:
        return None
    system, _, code = raw.rpartition("|")
    found = (
        s
        for s in known.values()
        if (not system or system == to.code_system_url(s.id)) and code in (s.code, str(s.id))
    )
    return next((s.id for s in found), _NOWHERE)


def _near(query: SearchQuery) -> Near | None:
    raw = query.first("near")
    if raw is None:
        return None
    parts = raw.split("|")
    try:
        latitude, longitude, distance = map(float, parts[:3])
    except ValueError as error:
        raise invalid_field("near", "Saisissez latitude|longitude|distance|km.") from error
    unit = parts[3] if len(parts) > 3 else "km"
    if unit not in ("km", "m"):
        raise invalid_field("near", "Saisissez la distance en km ou m.")
    return Near(latitude, longitude, distance if unit == "km" else distance / 1000)


def _specialties(who: Reader) -> dict[Id, SpecialtyRow]:
    return {s.id: s for s in _queries().specialties(SpecialtyFilter(), who).items}


class _Identified(Protocol):
    @property
    def id(self) -> Id: ...


def _entries[T: _Identified](
    rules: ResourceRules, rows: Sequence[T], build: Callable[[T], FhirModel], **include: bool
) -> list[BundleEntry]:
    return [entry(rules.type, str(r.id), _json(build(r)), **include) for r in rows]


# Organization: hospitals (`prov`) and departments (`dept`).
_ORGANIZATION_KINDS = {"prov": OrganizationKind.HOSPITAL, "dept": OrganizationKind.DEPARTMENT}


@router.get("/Organization/{resource_id}")
def read_organization(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = OrganizationFilter(ids=(_id(resource_id),))
    model = to.organization(_read(request, _queries().organizations(criteria, reader(request))))
    return _resource(model, model.meta.version_id or "")


@router.get("/Organization")
def search_organization(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, ORGANIZATION)
    criteria = OrganizationFilter(
        name=query.first("name"),
        kind=_choice(query, "type", _ORGANIZATION_KINDS),
        part_of=_ref(query, "partof", "Organization"),
        city=query.first("address-city"),
        active=_boolean(query, "active"),
    )
    page = _queries().organizations(criteria, reader(request), _paging(query))
    return _bundle(
        ORGANIZATION, query, page.total, _entries(ORGANIZATION, page.items, to.organization)
    )


# Location: hospital sites (`si`) and rooms (`ro`).
_LOCATION_KINDS = {"si": LocationKind.SITE, "ro": LocationKind.ROOM}


@router.get("/Location/{resource_id}")
def read_location(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = LocationFilter(ids=(_id(resource_id),))
    model = to.location(_read(request, _queries().locations(criteria, reader(request))))
    return _resource(model, model.meta.version_id or "")


@router.get("/Location")
def search_location(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, LOCATION)
    criteria = LocationFilter(
        name=query.first("name"),
        kind=_choice(query, "type", _LOCATION_KINDS),
        organization=_ref(query, "organization", "Organization"),
        part_of=_ref(query, "partof", "Location"),
        city=query.first("address-city"),
        near=_near(query),
    )
    page = _queries().locations(criteria, reader(request), _paging(query))
    return _bundle(LOCATION, query, page.total, _entries(LOCATION, page.items, to.location))


@router.get("/HealthcareService/{resource_id}")
def read_healthcare_service(request: HttpRequest, resource_id: str) -> HttpResponse:
    who = reader(request)
    criteria = ServiceFilter(ids=(_id(resource_id),))
    row = _read(request, _queries().services(criteria, who))
    model = to.healthcare_service(row, _specialties(who))
    return _resource(model, model.meta.version_id or "")


@router.get("/HealthcareService")
def search_healthcare_service(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, HEALTHCARE_SERVICE)
    who = reader(request)
    known = _specialties(who)
    criteria = ServiceFilter(
        name=query.first("name"),
        organization=_ref(query, "organization", "Organization"),
        specialty=_specialty_id(query, known),
        active=_boolean(query, "active"),
    )
    page = _queries().services(criteria, who, _paging(query))
    entries = _entries(HEALTHCARE_SERVICE, page.items, lambda r: to.healthcare_service(r, known))
    return _bundle(HEALTHCARE_SERVICE, query, page.total, entries)


_STATUSES = {"active": True, "retired": False}


@router.get("/CodeSystem/{resource_id}")
def read_code_system(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = SpecialtyFilter(ids=(_id(resource_id),))
    model = to.code_system(_read(request, _queries().specialties(criteria, reader(request))))
    return _resource(model, model.meta.version_id or "")


@router.get("/CodeSystem")
def search_code_system(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, CODE_SYSTEM)
    criteria = SpecialtyFilter(name=query.first("name"), active=_choice(query, "status", _STATUSES))
    page = _queries().specialties(criteria, reader(request), _paging(query))
    return _bundle(
        CODE_SYSTEM, query, page.total, _entries(CODE_SYSTEM, page.items, to.code_system)
    )


def _active_specialties() -> Sequence[SpecialtyRow]:
    return _queries().specialties(SpecialtyFilter(active=True), Reader.anonymous()).items


@router.get("/ValueSet/{resource_id}")
def read_value_set(request: HttpRequest, resource_id: str) -> HttpResponse:
    refuse_undeclared(request.GET, frozenset())
    rows = _active_specialties()
    if resource_id != to.SPECIALTIES or not rows:
        raise _missing()
    model = to.value_set(rows)
    return _resource(model, model.meta.version_id or "")


@router.get("/ValueSet")
def search_value_set(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, VALUE_SET)
    rows = _active_specialties()
    found = [to.value_set(rows)] if rows and query.page == 1 else []
    entries = [entry(VALUE_SET.type, to.SPECIALTIES, _json(m)) for m in found]
    return _bundle(VALUE_SET, query, 1 if rows else 0, entries)


@router.get("/Practitioner/{resource_id}")
def read_practitioner(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = PractitionerFilter(ids=(_id(resource_id),))
    model = to.practitioner(_read(request, _queries().practitioners(criteria, reader(request))))
    return _resource(model, model.meta.version_id or "")


@router.get("/Practitioner")
def search_practitioner(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, PRACTITIONER)
    criteria = PractitionerFilter(name=query.first("name"), active=_boolean(query, "active"))
    page = _queries().practitioners(criteria, reader(request), _paging(query))
    return _bundle(
        PRACTITIONER, query, page.total, _entries(PRACTITIONER, page.items, to.practitioner)
    )


@router.get("/PractitionerRole/{resource_id}")
def read_practitioner_role(request: HttpRequest, resource_id: str) -> HttpResponse:
    who = reader(request)
    row = _read(request, _queries().roles(RoleFilter(ids=(_id(resource_id),)), who))
    model = to.role(row, _specialties(who))
    return _resource(model, model.meta.version_id or "")


def _role_includes(query: SearchQuery, rows: Sequence[RoleRow], who: Reader) -> list[BundleEntry]:
    found: list[BundleEntry] = []
    if "PractitionerRole:practitioner" in query.includes and rows:
        ids = tuple(dict.fromkeys(r.practitioner_id for r in rows))
        people: Sequence[PractitionerRow] = (
            _queries().practitioners(PractitionerFilter(ids=ids), who).items
        )
        found += _entries(PRACTITIONER, people, to.practitioner, include=True)
    departments = tuple(dict.fromkeys(r.department_id for r in rows if r.department_id))
    if "PractitionerRole:organization" in query.includes and departments:
        organizations = _queries().organizations(OrganizationFilter(ids=departments), who).items
        found += _entries(ORGANIZATION, organizations, to.organization, include=True)
    return found


@router.get("/PractitionerRole")
def search_practitioner_role(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, PRACTITIONER_ROLE)
    who = reader(request)
    known = _specialties(who)
    criteria = RoleFilter(
        practitioner=_ref(query, "practitioner", "Practitioner"),
        organization=_ref(query, "organization", "Organization"),
        specialty=_specialty_id(query, known),
        location=_ref(query, "location", "Location"),
        service=_ref(query, "service", "HealthcareService"),
        active=_boolean(query, "active"),
    )
    page = _queries().roles(criteria, who, _paging(query))
    entries = _entries(PRACTITIONER_ROLE, page.items, lambda r: to.role(r, known))
    entries += _role_includes(query, page.items, who)
    return _bundle(PRACTITIONER_ROLE, query, page.total, entries)


@router.get("/Schedule/{resource_id}")
def read_schedule(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = ScheduleFilter(ids=(_id(resource_id),))
    model = to.schedule(_read(request, _queries().schedules(criteria, reader(request))))
    return _resource(model, model.meta.version_id or "")


def _horizon(query: SearchQuery) -> tuple[date | None, date | None]:
    """The planning horizon a `date` asks for: starting by and ending from which day."""
    raw = query.first("date")
    if raw is None:
        return None, None
    bound = date_bound("date", raw)
    day = bound.value.date() if isinstance(bound.value, datetime) else bound.value
    one = timedelta(days=1)
    return {
        Prefix.EQ: (day, day),
        Prefix.GE: (None, day),
        Prefix.GT: (None, day + one),
        Prefix.LE: (day, None),
        Prefix.LT: (day - one, None),
    }[bound.prefix]


@router.get("/Schedule")
def search_schedule(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, SCHEDULE)
    starts_by, ends_from = _horizon(query)
    criteria = ScheduleFilter(
        actor=_ref(query, "actor", "Practitioner", "Location"),
        starts_by=starts_by,
        ends_from=ends_from,
        active=_boolean(query, "active"),
    )
    page = _queries().schedules(criteria, reader(request), _paging(query))
    return _bundle(SCHEDULE, query, page.total, _entries(SCHEDULE, page.items, to.schedule))
