"""Reference writes on the directory router: the admin's console, the clinician's availability."""

from collections.abc import Callable, Sequence
from zoneinfo import ZoneInfo

from django.http import HttpRequest, HttpResponse

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity, Role
from drlibre.interfaces.fhir.access import caller, reader, require_admin
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.diff import changes
from drlibre.interfaces.fhir.mappers import directory as to
from drlibre.interfaces.fhir.mappers import directory_writes as writes
from drlibre.interfaces.fhir.mappers.schedule import (
    practitioner_of,
    schedule_fields,
    schedule_paths,
)
from drlibre.interfaces.fhir.outcome import fhir_response
from drlibre.interfaces.fhir.registry import ResourceRules
from drlibre.interfaces.fhir.routers.directory import (
    CODE_SYSTEM,
    HEALTHCARE_SERVICE,
    LOCATION,
    ORGANIZATION,
    PRACTITIONER,
    PRACTITIONER_ROLE,
    SCHEDULE,
    known_specialties,
    router,
)
from drlibre.interfaces.fhir.routing import (
    missing,
    parse_id,
    read_body,
    resource_response,
    version_of,
)
from drlibre.interfaces.fhir.schemas.common import FhirModel, Reference
from drlibre.interfaces.fhir.schemas.directory import (
    CodeSystem,
    HealthcareService,
    Location,
    Organization,
    Practitioner,
    PractitionerRole,
    Schedule,
)
from drlibre.interfaces.fhir.version import etag, expected_version
from drlibre.interop.application.ports.inbound import (
    DepartmentRow,
    DirectoryQueries,
    HospitalRow,
    LocationFilter,
    LocationKind,
    Locked,
    OrganizationFilter,
    PractitionerFilter,
    PractitionerRow,
    Reader,
    RoleFilter,
    RoleRow,
    RoomRow,
    ScheduleFilter,
    ScheduleRow,
    ServiceFilter,
    SpecialtyFilter,
    WriteTarget,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field
from drlibre.shared_kernel.validation import parse_id as parse_id_or_none

SITE_IS_AN_ORGANIZATION = "Le site s'écrit par son Organization `prov`."
ADMIN_ROLE_IS_A_USER = "Le rôle admin suit l'utilisateur : écrivez le Practitioner."
OWN_AVAILABILITY = "Seul le praticien gère ses plages et ses absences."
HORIZON_IS_COMPUTED = "L'horizon suit la période de validité de la plage."


def _queries() -> DirectoryQueries:
    return container().directory_queries


def _created(rules: ResourceRules, model: FhirModel, resource_id: Id, version: str) -> HttpResponse:
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=201)
    response["Location"] = f"{base_url()}/{rules.type}/{resource_id}"
    response["ETag"] = etag(version)
    return response


def _deleted() -> HttpResponse:
    return HttpResponse(status=204)


def _same_id(path: str, incoming: str | None, resource_id: str) -> None:
    if incoming not in (None, resource_id):
        raise invalid_field(path, "L'id doit être celui de l'adresse.")


def _update[T](
    request: HttpRequest,
    target: WriteTarget,
    current: Callable[[], str],
    write: Callable[[], T],
    *,
    all_or_nothing: bool = False,
) -> T:
    return container().conditional_writes.run(
        target=target,
        expected=expected_version(request.headers.get("If-Match")),
        current=current,
        write=write,
        all_or_nothing=all_or_nothing,
    )


def _one[T](items: Sequence[T]) -> T:
    if not items:
        raise missing()
    return items[0]


# Organization: a hospital (`prov`) or a department (`dept`).
def _organization(record_id: Id, who: Reader) -> HospitalRow | DepartmentRow:
    return _one(_queries().organizations(OrganizationFilter(ids=(record_id,)), who).items)


def _organization_model(record_id: Id, who: Reader) -> Organization:
    return to.organization(_organization(record_id, who))


def _save_organization(
    identity: Identity, record_id: Id | None, kind: str | None, incoming: Organization
) -> Id:
    actor = identity.user_id
    if kind == "prov":
        fields = writes.hospital_fields(incoming)
        return container().save_hospital.execute(actor=actor, record_id=record_id, fields=fields)
    if kind == "dept":
        fields = writes.department_fields(incoming)
        return container().save_department.execute(actor=actor, record_id=record_id, fields=fields)
    raise invalid_field("Organization.type", "Choisissez le type prov ou dept.")


@router.post("/Organization")
def create_organization(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    incoming = read_body(request, Organization)
    kind = writes.organization_kind(incoming)
    created = _save_organization(identity, None, kind, incoming)
    model = _organization_model(created, reader(request))
    return _created(ORGANIZATION, model, created, version_of(model))


def _kind_of(row: HospitalRow | DepartmentRow) -> str:
    return "dept" if isinstance(row, DepartmentRow) else "prov"


@router.put("/Organization/{resource_id}")
def update_organization(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    kind = _kind_of(_organization(record_id, who))
    incoming = read_body(request, Organization)
    _same_id("Organization.id", incoming.id, resource_id)
    if writes.organization_kind(incoming) != kind:
        raise invalid_field("Organization.type", "Le type d'une organisation ne change pas.")
    locked = Locked.DEPARTMENT if kind == "dept" else Locked.HOSPITAL
    _update(
        request,
        WriteTarget.record(locked, record_id),
        lambda: version_of(_organization_model(record_id, who)),
        lambda: _save_organization(identity, record_id, kind, incoming),
    )
    model = _organization_model(record_id, who)
    return resource_response(model, version_of(model))


@router.delete("/Organization/{resource_id}")
def delete_organization(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    row = _organization(record_id, reader(request))
    if isinstance(row, DepartmentRow):
        container().delete_department.execute(actor=identity.user_id, record_id=record_id)
    else:
        container().delete_hospital.execute(actor=identity.user_id, record_id=record_id)
    return _deleted()


# Location: rooms only; a hospital site is read from its Organization.
def _room(record_id: Id, who: Reader) -> RoomRow:
    row = _one(_queries().locations(LocationFilter(ids=(record_id,)), who).items)
    if not isinstance(row, RoomRow):
        raise invalid_field("Location.physicalType", SITE_IS_AN_ORGANIZATION)
    return row


def _room_body(request: HttpRequest) -> Location:
    incoming = read_body(request, Location)
    if writes.location_kind(incoming) != "ro":
        raise invalid_field("Location.physicalType", SITE_IS_AN_ORGANIZATION)
    return incoming


@router.post("/Location")
def create_location(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    fields = writes.room_fields(_room_body(request))
    created = container().save_room.execute(actor=identity.user_id, record_id=None, fields=fields)
    model = to.location(_room(created, reader(request)))
    return _created(LOCATION, model, created, version_of(model))


@router.put("/Location/{resource_id}")
def update_location(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    _room(record_id, who)
    incoming = _room_body(request)
    _same_id("Location.id", incoming.id, resource_id)
    fields = writes.room_fields(incoming)
    _update(
        request,
        WriteTarget.record(Locked.ROOM, record_id),
        lambda: version_of(to.location(_room(record_id, who))),
        lambda: container().save_room.execute(
            actor=identity.user_id, record_id=record_id, fields=fields
        ),
    )
    model = to.location(_room(record_id, who))
    return resource_response(model, version_of(model))


@router.delete("/Location/{resource_id}")
def delete_location(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    _room(record_id, reader(request))
    container().delete_room.execute(actor=identity.user_id, record_id=record_id)
    return _deleted()


# HealthcareService: appointment types.
def _service_model(record_id: Id, who: Reader) -> HealthcareService:
    row = _one(_queries().services(ServiceFilter(ids=(record_id,)), who).items)
    return to.healthcare_service(row, known_specialties(who))


@router.post("/HealthcareService")
def create_healthcare_service(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    fields = writes.type_fields(read_body(request, HealthcareService))
    created = container().save_appointment_type.execute(
        actor=identity.user_id, record_id=None, fields=fields
    )
    model = _service_model(created, reader(request))
    return _created(HEALTHCARE_SERVICE, model, created, version_of(model))


@router.put("/HealthcareService/{resource_id}")
def update_healthcare_service(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    _service_model(record_id, who)
    incoming = read_body(request, HealthcareService)
    _same_id("HealthcareService.id", incoming.id, resource_id)
    fields = writes.type_fields(incoming)
    _update(
        request,
        WriteTarget.record(Locked.APPOINTMENT_TYPE, record_id),
        lambda: version_of(_service_model(record_id, who)),
        lambda: container().save_appointment_type.execute(
            actor=identity.user_id, record_id=record_id, fields=fields
        ),
    )
    model = _service_model(record_id, who)
    return resource_response(model, version_of(model))


@router.delete("/HealthcareService/{resource_id}")
def delete_healthcare_service(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    _service_model(record_id, reader(request))
    container().delete_appointment_type.execute(actor=identity.user_id, record_id=record_id)
    return _deleted()


# CodeSystem: one specialty each; the `specialties` ValueSet follows them, read-only.
def _code_system(record_id: Id, who: Reader) -> CodeSystem:
    return to.code_system(
        _one(_queries().specialties(SpecialtyFilter(ids=(record_id,)), who).items)
    )


@router.post("/CodeSystem")
def create_code_system(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    fields = writes.specialty_fields(read_body(request, CodeSystem))
    created = container().save_specialty.execute(
        actor=identity.user_id, record_id=None, fields=fields
    )
    model = _code_system(created, reader(request))
    return _created(CODE_SYSTEM, model, created, version_of(model))


@router.put("/CodeSystem/{resource_id}")
def update_code_system(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    _code_system(record_id, who)
    incoming = read_body(request, CodeSystem)
    _same_id("CodeSystem.id", incoming.id, resource_id)
    fields = writes.specialty_fields(incoming)
    _update(
        request,
        WriteTarget.record(Locked.SPECIALTY, record_id),
        lambda: version_of(_code_system(record_id, who)),
        lambda: container().save_specialty.execute(
            actor=identity.user_id, record_id=record_id, fields=fields
        ),
    )
    model = _code_system(record_id, who)
    return resource_response(model, version_of(model))


@router.delete("/CodeSystem/{resource_id}")
def delete_code_system(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    _code_system(record_id, reader(request))
    container().delete_specialty.execute(actor=identity.user_id, record_id=record_id)
    return _deleted()


# Practitioner: a clinician or admin user, through the console's user use cases.
def _practitioner(record_id: Id, who: Reader) -> PractitionerRow:
    return _one(_queries().practitioners(PractitionerFilter(ids=(record_id,)), who).items)


_ROLES = frozenset({"clinician", "admin"})


def _staff_role(raw: str | None, current: str) -> str:
    role = raw or current
    if role not in _ROLES:
        raise invalid_field("role", "Choisissez le rôle clinician ou admin.")
    return role


@router.post("/Practitioner")
def create_practitioner(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    values = writes.user_values(read_body(request, Practitioner))
    created = container().save_user.execute(
        actor=identity.user_id,
        user_id=None,
        full_name=values.full_name,
        email=values.email,
        role=_staff_role(values.role, "clinician"),
        active=values.active,
        temporary_password=values.temporary_password,
    )
    model = to.practitioner(_practitioner(created, reader(request)))
    return _created(PRACTITIONER, model, created, version_of(model))


@router.put("/Practitioner/{resource_id}")
def update_practitioner(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    _practitioner(record_id, who)
    incoming = read_body(request, Practitioner)
    _same_id("Practitioner.id", incoming.id, resource_id)
    values = writes.user_values(incoming)

    def write() -> None:
        before = _practitioner(record_id, who)
        current = writes.practitioner_paths(to.practitioner(before))
        changes(
            current,
            writes.practitioner_paths(incoming),
            writable=writes.PRACTITIONER_WRITABLE,
        )
        container().save_user.execute(
            actor=identity.user_id,
            user_id=record_id,
            full_name=values.full_name,
            email=values.email,
            role=_staff_role(values.role, "admin" if before.is_admin else "clinician"),
            active=values.active,
            temporary_password=values.temporary_password,
        )

    _update(
        request,
        WriteTarget.user(user_id=record_id),
        lambda: version_of(to.practitioner(_practitioner(record_id, who))),
        write,
    )
    model = to.practitioner(_practitioner(record_id, who))
    return resource_response(model, version_of(model))


@router.delete("/Practitioner/{resource_id}")
def delete_practitioner(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    _practitioner(record_id, reader(request))
    container().delete_user.execute(actor=identity.user_id, user_id=record_id)
    return _deleted()


# PractitionerRole: a clinician profile; an admin's role follows their user.
def _role(record_id: Id, who: Reader) -> RoleRow:
    row = _one(_queries().roles(RoleFilter(ids=(record_id,)), who).items)
    if row.is_admin:
        raise invalid_field("PractitionerRole.code", ADMIN_ROLE_IS_A_USER)
    return row


def _role_model(record_id: Id, who: Reader) -> PractitionerRole:
    return to.role(_role(record_id, who), known_specialties(who))


def _default_room(places: tuple[Reference, ...] | None, who: Reader) -> str:
    """The room among the role's locations; its hospital site is computed, so left aside."""
    ids = []
    for place in places or ():
        raw = writes.reference_id(place, "Location")
        found = parse_id_or_none(raw)
        if found is None:
            raise invalid_field("PractitionerRole.location", "Saisissez Location/<id>.")
        ids.append(found)
    criteria = LocationFilter(ids=tuple(ids), kind=LocationKind.ROOM)
    rooms = _queries().locations(criteria, who).items if ids else ()
    if len(rooms) > 1:
        raise invalid_field("PractitionerRole.location", "Nommez une seule salle par défaut.")
    return str(rooms[0].id) if rooms else ""


def _title(practitioner_id: str, who: Reader) -> str:
    found = parse_id_or_none(practitioner_id)
    rows = _queries().practitioners(PractitionerFilter(ids=(found,)), who).items if found else ()
    return (rows[0].title or "") if rows else ""


@router.post("/PractitionerRole")
def create_practitioner_role(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    who = reader(request)
    incoming = read_body(request, PractitionerRole)
    user_id = writes.reference_id(incoming.practitioner, "Practitioner")
    fields = writes.profile_fields(
        incoming, room_id=_default_room(incoming.location, who), title=""
    )
    created = container().attach_clinician_profile.execute(
        actor=identity.user_id, user_id=user_id, fields=fields
    )
    model = _role_model(created, who)
    return _created(PRACTITIONER_ROLE, model, created, version_of(model))


@router.put("/PractitionerRole/{resource_id}")
def update_practitioner_role(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    if identity.role is not Role.ADMIN:
        return _update_own_time_off(request, identity, resource_id)
    who = reader(request)
    record_id = parse_id(resource_id)
    _role(record_id, who)
    incoming = read_body(request, PractitionerRole)
    _same_id("PractitionerRole.id", incoming.id, resource_id)
    room_id = _default_room(incoming.location, who)

    def write() -> None:
        current = _role_model(record_id, who)
        changes(
            writes.role_paths(current),
            writes.role_paths(incoming),
            writable=frozenset(),
            reserved=frozenset({"PractitionerRole.availableTime", "PractitionerRole.notAvailable"}),
        )
        title = _title(writes.reference_id(current.practitioner, "Practitioner"), who)
        container().edit_clinician_profile.execute(
            actor=identity.user_id,
            profile_id=record_id,
            fields=writes.profile_fields(incoming, room_id=room_id, title=title),
        )

    _update(
        request,
        WriteTarget.clinician(clinician_id=record_id),
        lambda: version_of(_role_model(record_id, who)),
        write,
    )
    model = _role_model(record_id, who)
    return resource_response(model, version_of(model))


def _zone(row: RoleRow, who: Reader) -> ZoneInfo:
    """The hospital zone the time off screen reads its local dates in."""
    site = _organization(row.hospital_id, who) if row.hospital_id else None
    if not isinstance(site, HospitalRow):
        raise missing()
    return ZoneInfo(site.time_zone)


def _update_own_time_off(
    request: HttpRequest, identity: Identity, resource_id: str
) -> HttpResponse:
    """A clinician's own role: `notAvailable` alone changes, every period or none."""
    who = reader(request)
    record_id = parse_id(resource_id)
    if who.profile_id != record_id:
        raise DomainError(ErrorCode.FORBIDDEN, OWN_AVAILABILITY)
    incoming = read_body(request, PractitionerRole)
    _same_id("PractitionerRole.id", incoming.id, resource_id)

    def write() -> None:
        row = _role(record_id, who)
        current = to.role(row, known_specialties(who))
        paths = writes.own_role_paths(current)
        asked = writes.own_role_paths(incoming)
        changes(paths, asked, writable=frozenset(), reserved=frozenset(paths | asked))
        found = writes.time_off_changes(
            row.time_offs, incoming.not_available or (), _zone(row, who)
        )
        for time_off_id in found.removed:
            container().delete_time_off.execute(actor=identity.user_id, time_off_id=time_off_id)
        for fields in found.added:
            container().record_time_off.execute(actor=identity.user_id, fields=fields)

    _update(
        request,
        WriteTarget.clinician(clinician_id=record_id),
        lambda: version_of(_role_model(record_id, who)),
        write,
        all_or_nothing=True,
    )
    model = _role_model(record_id, who)
    return resource_response(model, version_of(model))


@router.delete("/PractitionerRole/{resource_id}")
def delete_practitioner_role(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    record_id = parse_id(resource_id)
    _role(record_id, reader(request))
    container().delete_clinician_profile.execute(actor=identity.user_id, profile_id=record_id)
    return _deleted()


# Schedule: one availability rule, written by its clinician as on the workspace screen.
def _schedule(record_id: Id, who: Reader) -> ScheduleRow:
    return _one(_queries().schedules(ScheduleFilter(ids=(record_id,)), who).items)


def _named_self(practitioner_id: str, identity: Identity) -> None:
    """A schedule names its practitioner: only the token holder themselves."""
    if practitioner_id != str(identity.user_id):
        raise DomainError(ErrorCode.FORBIDDEN, OWN_AVAILABILITY)


@router.post("/Schedule")
def create_schedule(request: HttpRequest) -> HttpResponse:
    identity = caller(request)
    incoming = read_body(request, Schedule)
    _named_self(practitioner_of(incoming), identity)
    if incoming.planning_horizon is not None:
        raise invalid_field("Schedule.planningHorizon", HORIZON_IS_COMPUTED)
    created = container().save_availability_rule.execute(
        actor=identity.user_id, rule_id=None, fields=schedule_fields(incoming)
    )
    model = to.schedule(_schedule(created, reader(request)))
    return _created(SCHEDULE, model, created, version_of(model))


@router.put("/Schedule/{resource_id}")
def update_schedule(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    who = reader(request)
    record_id = parse_id(resource_id)
    row = _schedule(record_id, who)
    _named_self(str(row.practitioner_id), identity)
    incoming = read_body(request, Schedule)
    _same_id("Schedule.id", incoming.id, resource_id)

    def write() -> None:
        current = to.schedule(_schedule(record_id, who))
        changes(schedule_paths(current), schedule_paths(incoming), writable=frozenset())
        container().save_availability_rule.execute(
            actor=identity.user_id, rule_id=record_id, fields=schedule_fields(incoming)
        )

    _update(
        request,
        WriteTarget.clinician(clinician_id=row.role_id, row=(Locked.AVAILABILITY_RULE, record_id)),
        lambda: version_of(to.schedule(_schedule(record_id, who))),
        write,
    )
    model = to.schedule(_schedule(record_id, who))
    return resource_response(model, version_of(model))


@router.delete("/Schedule/{resource_id}")
def delete_schedule(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    record_id = parse_id(resource_id)
    container().delete_availability_rule.execute(actor=identity.user_id, rule_id=record_id)
    return _deleted()
