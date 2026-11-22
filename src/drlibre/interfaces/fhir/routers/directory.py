import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import reader
from drlibre.interfaces.fhir.bundle import entry
from drlibre.interfaces.fhir.mappers import directory as to
from drlibre.interfaces.fhir.params import (
    Prefix,
    SearchQuery,
    date_bound,
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
from drlibre.interfaces.fhir.routing import (
    boolean,
    bundle_response,
    choice,
    entries_of,
    json_of,
    missing,
    paging_of,
    parse_id,
    read_one,
    reference,
    resource_response,
    version_of,
)
from drlibre.interfaces.fhir.schemas.bundle import BundleEntry
from drlibre.interop.application.ports.inbound import (
    DirectoryQueries,
    LocationFilter,
    LocationKind,
    Near,
    OrganizationFilter,
    OrganizationKind,
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
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["directory"])

_READ_SEARCH = (Interaction.READ, Interaction.SEARCH)
# The admin writes these as on the console; `routers/reference_writes.py` serves the writes.
_MANAGED = (*_READ_SEARCH, Interaction.CREATE, Interaction.UPDATE, Interaction.DELETE)
_STRING, _TOKEN, _REFERENCE = ParamType.STRING, ParamType.TOKEN, ParamType.REFERENCE
_DATE = ParamType.DATE

ORGANIZATION = declare(
    ResourceRules(
        type="Organization",
        interactions=_MANAGED,
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
        interactions=_MANAGED,
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
        interactions=_MANAGED,
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
        interactions=_MANAGED,
        search=(SearchParam("name", _STRING), SearchParam("status", _TOKEN)),
    )
)
VALUE_SET = declare(ResourceRules(type="ValueSet", interactions=_READ_SEARCH))
PRACTITIONER = declare(
    ResourceRules(
        type="Practitioner",
        interactions=_MANAGED,
        search=(SearchParam("name", _STRING), SearchParam("active", _TOKEN)),
        sorts=("name",),
    )
)
PRACTITIONER_ROLE = declare(
    ResourceRules(
        type="PractitionerRole",
        interactions=_MANAGED,
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


def _queries() -> DirectoryQueries:
    return container().directory_queries


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


def known_specialties(who: Reader) -> dict[Id, SpecialtyRow]:
    return {s.id: s for s in _queries().specialties(SpecialtyFilter(), who).items}


# Organization: hospitals (`prov`) and departments (`dept`).
_ORGANIZATION_KINDS = {"prov": OrganizationKind.HOSPITAL, "dept": OrganizationKind.DEPARTMENT}


@router.get("/Organization/{resource_id}")
def read_organization(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = OrganizationFilter(ids=(parse_id(resource_id),))
    model = to.organization(read_one(request, _queries().organizations(criteria, reader(request))))
    return resource_response(model, version_of(model))


@router.get("/Organization")
def search_organization(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, ORGANIZATION)
    criteria = OrganizationFilter(
        name=query.first("name"),
        kind=choice(query, "type", _ORGANIZATION_KINDS),
        part_of=reference(query, "partof", "Organization"),
        city=query.first("address-city"),
        active=boolean(query, "active"),
    )
    page = _queries().organizations(criteria, reader(request), paging_of(query))
    return bundle_response(
        ORGANIZATION, query, page.total, entries_of(ORGANIZATION, page.items, to.organization)
    )


# Location: hospital sites (`si`) and rooms (`ro`).
_LOCATION_KINDS = {"si": LocationKind.SITE, "ro": LocationKind.ROOM}


@router.get("/Location/{resource_id}")
def read_location(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = LocationFilter(ids=(parse_id(resource_id),))
    model = to.location(read_one(request, _queries().locations(criteria, reader(request))))
    return resource_response(model, version_of(model))


@router.get("/Location")
def search_location(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, LOCATION)
    criteria = LocationFilter(
        name=query.first("name"),
        kind=choice(query, "type", _LOCATION_KINDS),
        organization=reference(query, "organization", "Organization"),
        part_of=reference(query, "partof", "Location"),
        city=query.first("address-city"),
        near=_near(query),
    )
    page = _queries().locations(criteria, reader(request), paging_of(query))
    return bundle_response(
        LOCATION, query, page.total, entries_of(LOCATION, page.items, to.location)
    )


@router.get("/HealthcareService/{resource_id}")
def read_healthcare_service(request: HttpRequest, resource_id: str) -> HttpResponse:
    who = reader(request)
    criteria = ServiceFilter(ids=(parse_id(resource_id),))
    row = read_one(request, _queries().services(criteria, who))
    model = to.healthcare_service(row, known_specialties(who))
    return resource_response(model, version_of(model))


@router.get("/HealthcareService")
def search_healthcare_service(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, HEALTHCARE_SERVICE)
    who = reader(request)
    known = known_specialties(who)
    criteria = ServiceFilter(
        name=query.first("name"),
        organization=reference(query, "organization", "Organization"),
        specialty=_specialty_id(query, known),
        active=boolean(query, "active"),
    )
    page = _queries().services(criteria, who, paging_of(query))
    entries = entries_of(HEALTHCARE_SERVICE, page.items, lambda r: to.healthcare_service(r, known))
    return bundle_response(HEALTHCARE_SERVICE, query, page.total, entries)


_STATUSES = {"active": True, "retired": False}


@router.get("/CodeSystem/{resource_id}")
def read_code_system(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = SpecialtyFilter(ids=(parse_id(resource_id),))
    model = to.code_system(read_one(request, _queries().specialties(criteria, reader(request))))
    return resource_response(model, version_of(model))


@router.get("/CodeSystem")
def search_code_system(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, CODE_SYSTEM)
    criteria = SpecialtyFilter(name=query.first("name"), active=choice(query, "status", _STATUSES))
    page = _queries().specialties(criteria, reader(request), paging_of(query))
    return bundle_response(
        CODE_SYSTEM, query, page.total, entries_of(CODE_SYSTEM, page.items, to.code_system)
    )


def _active_specialties() -> Sequence[SpecialtyRow]:
    return _queries().specialties(SpecialtyFilter(active=True), Reader.anonymous()).items


@router.get("/ValueSet/{resource_id}")
def read_value_set(request: HttpRequest, resource_id: str) -> HttpResponse:
    refuse_undeclared(request.GET, frozenset())
    rows = _active_specialties()
    if resource_id != to.SPECIALTIES or not rows:
        raise missing()
    model = to.value_set(rows)
    return resource_response(model, version_of(model))


@router.get("/ValueSet")
def search_value_set(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, VALUE_SET)
    rows = _active_specialties()
    found = [to.value_set(rows)] if rows and query.page == 1 else []
    entries = [entry(VALUE_SET.type, to.SPECIALTIES, json_of(m)) for m in found]
    return bundle_response(VALUE_SET, query, 1 if rows else 0, entries)


@router.get("/Practitioner/{resource_id}")
def read_practitioner(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = PractitionerFilter(ids=(parse_id(resource_id),))
    model = to.practitioner(read_one(request, _queries().practitioners(criteria, reader(request))))
    return resource_response(model, version_of(model))


@router.get("/Practitioner")
def search_practitioner(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, PRACTITIONER)
    criteria = PractitionerFilter(name=query.first("name"), active=boolean(query, "active"))
    page = _queries().practitioners(criteria, reader(request), paging_of(query))
    return bundle_response(
        PRACTITIONER, query, page.total, entries_of(PRACTITIONER, page.items, to.practitioner)
    )


@router.get("/PractitionerRole/{resource_id}")
def read_practitioner_role(request: HttpRequest, resource_id: str) -> HttpResponse:
    who = reader(request)
    row = read_one(request, _queries().roles(RoleFilter(ids=(parse_id(resource_id),)), who))
    model = to.role(row, known_specialties(who))
    return resource_response(model, version_of(model))


def _role_includes(query: SearchQuery, rows: Sequence[RoleRow], who: Reader) -> list[BundleEntry]:
    found: list[BundleEntry] = []
    if "PractitionerRole:practitioner" in query.includes and rows:
        ids = tuple(dict.fromkeys(r.practitioner_id for r in rows))
        people: Sequence[PractitionerRow] = (
            _queries().practitioners(PractitionerFilter(ids=ids), who).items
        )
        found += entries_of(PRACTITIONER, people, to.practitioner, include=True)
    departments = tuple(dict.fromkeys(r.department_id for r in rows if r.department_id))
    if "PractitionerRole:organization" in query.includes and departments:
        organizations = _queries().organizations(OrganizationFilter(ids=departments), who).items
        found += entries_of(ORGANIZATION, organizations, to.organization, include=True)
    return found


@router.get("/PractitionerRole")
def search_practitioner_role(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, PRACTITIONER_ROLE)
    who = reader(request)
    known = known_specialties(who)
    criteria = RoleFilter(
        practitioner=reference(query, "practitioner", "Practitioner"),
        organization=reference(query, "organization", "Organization"),
        specialty=_specialty_id(query, known),
        location=reference(query, "location", "Location"),
        service=reference(query, "service", "HealthcareService"),
        active=boolean(query, "active"),
    )
    page = _queries().roles(criteria, who, paging_of(query))
    entries = entries_of(PRACTITIONER_ROLE, page.items, lambda r: to.role(r, known))
    entries += _role_includes(query, page.items, who)
    return bundle_response(PRACTITIONER_ROLE, query, page.total, entries)


@router.get("/Schedule/{resource_id}")
def read_schedule(request: HttpRequest, resource_id: str) -> HttpResponse:
    criteria = ScheduleFilter(ids=(parse_id(resource_id),))
    model = to.schedule(read_one(request, _queries().schedules(criteria, reader(request))))
    return resource_response(model, version_of(model))


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
        actor=reference(query, "actor", "Practitioner", "Location"),
        starts_by=starts_by,
        ends_from=ends_from,
        active=boolean(query, "active"),
    )
    page = _queries().schedules(criteria, reader(request), paging_of(query))
    return bundle_response(
        SCHEDULE, query, page.total, entries_of(SCHEDULE, page.items, to.schedule)
    )
