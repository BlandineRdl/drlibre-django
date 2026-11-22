from collections.abc import Mapping, Sequence

from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.schemas.common import (
    Address,
    CodeableConcept,
    Coding,
    ContactPoint,
    Extension,
    HumanName,
    Identifier,
    Meta,
    Period,
    Reference,
)
from drlibre.interfaces.fhir.schemas.directory import (
    AvailableTime,
    CodeSystem,
    Concept,
    HealthcareService,
    Location,
    NotAvailable,
    Organization,
    Position,
    Practitioner,
    PractitionerRole,
    Schedule,
    ValueSet,
    ValueSetCompose,
    ValueSetInclude,
)
from drlibre.interfaces.fhir.version import meta, version_id
from drlibre.interop.application.ports.inbound import (
    DepartmentRow,
    HospitalRow,
    PractitionerRow,
    RoleRow,
    RoomRow,
    ScheduleRow,
    ServiceRow,
    SpecialtyRow,
)
from drlibre.shared_kernel.ids import Id

ORGANIZATION_TYPE = "http://terminology.hl7.org/CodeSystem/organization-type"
PHYSICAL_TYPE = "http://terminology.hl7.org/CodeSystem/location-physical-type"
PRODUCT_CODE = "urn:drlibre:code"
ROLE_CODE = "urn:drlibre:role"
SPECIALTIES = "specialties"
# Weekday 0 is Sunday, as in availability rules.
DAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
UNAVAILABLE = "Indisponible"

type Specialties = Mapping[Id, SpecialtyRow]


def extension_url(name: str) -> str:
    return f"{base_url()}/StructureDefinition/{name}"


def code_system_url(specialty_id: Id) -> str:
    return f"{base_url()}/CodeSystem/{specialty_id}"


def _ref(resource_type: str, resource_id: Id) -> Reference:
    return Reference(reference=f"{resource_type}/{resource_id}")


def _code(value: str) -> tuple[Identifier, ...]:
    return (Identifier(system=PRODUCT_CODE, value=value),)


def _simple(row_meta: HospitalRow | DepartmentRow | RoomRow | ServiceRow | SpecialtyRow) -> Meta:
    return meta(version_id(row_meta.updated_at), row_meta.updated_at)


def _specialty(specialty: SpecialtyRow) -> CodeableConcept:
    coding = Coding(
        system=code_system_url(specialty.id), code=specialty.code, display=specialty.name
    )
    return CodeableConcept(coding=(coding,), text=specialty.name)


def _specialties(
    ids: Sequence[Id | None], known: Specialties
) -> tuple[CodeableConcept, ...] | None:
    found = tuple(_specialty(known[i]) for i in ids if i is not None and i in known)
    return found or None


def _site_extensions(h: HospitalRow) -> tuple[Extension, ...]:
    found = [Extension(url=extension_url("time-zone"), value_code=h.time_zone)]
    if h.latitude is not None and h.longitude is not None:
        position = (
            Extension(url="latitude", value_decimal=h.latitude),
            Extension(url="longitude", value_decimal=h.longitude),
        )
        found.append(Extension(url=extension_url("position"), extension=position))
    return tuple(found)


def _address(h: HospitalRow) -> Address:
    return Address(line=(h.street,), city=h.city, postal_code=h.postal_code, country=h.country)


def _phone(value: str | None) -> tuple[ContactPoint, ...] | None:
    return (ContactPoint(system="phone", value=value),) if value else None


def _description(value: str) -> tuple[Extension, ...]:
    return (Extension(url=extension_url("description"), value_string=value),) if value else ()


def organization(row: HospitalRow | DepartmentRow) -> Organization:
    """A hospital (`prov`) or one of its departments (`dept`, `partOf` it)."""
    if isinstance(row, DepartmentRow):
        return Organization(
            id=str(row.id),
            meta=_simple(row),
            extension=_description(row.description) or None,
            identifier=_code(row.code),
            active=row.active,
            type=(CodeableConcept(coding=(Coding(system=ORGANIZATION_TYPE, code="dept"),)),),
            name=row.name,
            part_of=_ref("Organization", row.hospital_id),
        )
    return Organization(
        id=str(row.id),
        meta=_simple(row),
        extension=(*_site_extensions(row), *_description(row.description)),
        identifier=_code(row.code),
        active=row.active,
        type=(CodeableConcept(coding=(Coding(system=ORGANIZATION_TYPE, code="prov"),)),),
        name=row.name,
        telecom=_phone(row.phone),
        address=(_address(row),),
    )


def location(row: HospitalRow | RoomRow) -> Location:
    """A hospital site (same id as its Organization) or a room `partOf` it."""
    if isinstance(row, RoomRow):
        extensions = (
            Extension(url=extension_url("floor"), value_string=row.floor),
            Extension(url=extension_url("capacity"), value_integer=row.capacity),
            *(Extension(url=extension_url("equipment"), value_string=e) for e in row.equipment),
        )
        return Location(
            id=str(row.id),
            meta=_simple(row),
            extension=extensions,
            identifier=_code(row.code),
            status="active" if row.active else "inactive",
            name=row.name,
            physical_type=CodeableConcept(coding=(Coding(system=PHYSICAL_TYPE, code="ro"),)),
            managing_organization=_ref("Organization", row.department_id),
            part_of=_ref("Location", row.hospital_id),
        )
    position = (
        Position(longitude=row.longitude, latitude=row.latitude)
        if row.latitude is not None and row.longitude is not None
        else None
    )
    return Location(
        id=str(row.id),
        meta=_simple(row),
        extension=(Extension(url=extension_url("time-zone"), value_code=row.time_zone),),
        identifier=_code(row.code),
        status="active" if row.active else "inactive",
        name=row.name,
        description=row.description or None,
        physical_type=CodeableConcept(coding=(Coding(system=PHYSICAL_TYPE, code="si"),)),
        telecom=_phone(row.phone),
        address=_address(row),
        position=position,
        managing_organization=_ref("Organization", row.id),
    )


def healthcare_service(row: ServiceRow, known: Specialties) -> HealthcareService:
    """An appointment type provided by its department, its settings as extensions."""
    extensions = (
        Extension(url=extension_url("duration-minutes"), value_integer=row.duration_minutes),
        Extension(url=extension_url("buffer-minutes"), value_integer=row.buffer_minutes),
        Extension(url=extension_url("colour"), value_string=row.colour),
        Extension(url=extension_url("needs-room"), value_boolean=row.needs_room),
        Extension(url=extension_url("bookable-online"), value_boolean=row.bookable_online),
    )
    return HealthcareService(
        id=str(row.id),
        meta=_simple(row),
        extension=extensions,
        identifier=_code(row.code),
        active=row.active,
        provided_by=_ref("Organization", row.department_id),
        specialty=_specialties(row.specialty_ids, known),
        name=row.name,
    )


def code_system(row: SpecialtyRow) -> CodeSystem:
    """One specialty, its own code system with a single concept."""
    return CodeSystem(
        id=str(row.id),
        meta=_simple(row),
        url=code_system_url(row.id),
        identifier=_code(row.code),
        name=row.code,
        title=row.name,
        status="active" if row.active else "retired",
        concept=(Concept(code=row.code, display=row.name),),
    )


def value_set(rows: Sequence[SpecialtyRow]) -> ValueSet:
    """Every active specialty's code system, gathered; versioned by all of them."""
    version = version_id(*(f"{r.id}@{r.updated_at}" for r in rows))
    return ValueSet(
        id=SPECIALTIES,
        meta=meta(version, max(r.updated_at for r in rows)),
        url=f"{base_url()}/ValueSet/{SPECIALTIES}",
        name="Specialties",
        title="Spécialités",
        compose=ValueSetCompose(
            include=tuple(ValueSetInclude(system=code_system_url(r.id)) for r in rows)
        ),
    )


def practitioner(row: PractitionerRow) -> Practitioner:
    """Name and title for anyone; email and phone only when the row carries them."""
    telecom = (
        *((ContactPoint(system="email", value=row.email),) if row.email else ()),
        *(_phone(row.phone) or ()),
    )
    return Practitioner(
        id=str(row.id),
        meta=meta(version_id(row.updated_at), row.updated_at),
        active=row.active,
        name=(HumanName(text=row.full_name, prefix=(row.title,) if row.title else None),),
        telecom=telecom or None,
    )


def _role_meta(row: RoleRow) -> Meta:
    stamps = [row.updated_at, *(a.updated_at for a in row.availability)]
    stamps += [o.updated_at for o in row.time_offs]
    version = version_id(
        row.updated_at,
        *(f"{a.id}@{a.updated_at}" for a in row.availability),
        *(f"{o.id}@{o.updated_at}" for o in row.time_offs),
    )
    return meta(version, max(stamps))


def _admin_role(row: RoleRow) -> PractitionerRole:
    return PractitionerRole(
        id=str(row.id),
        meta=_role_meta(row),
        active=row.active,
        practitioner=_ref("Practitioner", row.practitioner_id),
        code=(CodeableConcept(coding=(Coding(system=ROLE_CODE, code="admin"),)),),
    )


def _role_extensions(row: RoleRow) -> tuple[Extension, ...] | None:
    found = []
    if row.bio:
        found.append(Extension(url=extension_url("bio"), value_string=row.bio))
    if row.weight is not None:
        found.append(Extension(url=extension_url("round-robin-weight"), value_integer=row.weight))
    return tuple(found) or None


def _hours(row: RoleRow) -> tuple[AvailableTime, ...] | None:
    found = tuple(
        AvailableTime(
            days_of_week=(DAYS[a.weekday],),
            available_start_time=a.start.isoformat(),
            available_end_time=a.end.isoformat(),
        )
        for a in row.availability
    )
    return found or None


def _time_off(row: RoleRow) -> tuple[NotAvailable, ...] | None:
    found = tuple(
        NotAvailable(
            description=o.reason or UNAVAILABLE,
            during=Period(start=o.start.isoformat(), end=o.end.isoformat()),
        )
        for o in row.time_offs
    )
    return found or None


def role(row: RoleRow, known: Specialties) -> PractitionerRole:
    """A clinician's profile with its hours and time off, or an admin coded `admin`."""
    if row.is_admin:
        return _admin_role(row)
    places = tuple(
        _ref("Location", i) for i in (row.hospital_id, row.default_room_id) if i is not None
    )
    services = tuple(_ref("HealthcareService", i) for i in row.service_ids)
    return PractitionerRole(
        id=str(row.id),
        meta=_role_meta(row),
        extension=_role_extensions(row),
        active=row.active,
        practitioner=_ref("Practitioner", row.practitioner_id),
        organization=_ref("Organization", row.department_id) if row.department_id else None,
        specialty=_specialties((row.specialty_id,), known),
        location=places or None,
        healthcare_service=services or None,
        available_time=_hours(row),
        not_available=_time_off(row),
    )


def schedule(row: ScheduleRow) -> Schedule:
    """One availability rule: its clinician and room, horizon, weekly hours as an extension."""
    hours = (
        Extension(url="weekday", value_code=DAYS[row.weekday]),
        Extension(url="start", value_time=row.start.isoformat()),
        Extension(url="end", value_time=row.end.isoformat()),
        Extension(url="step-minutes", value_integer=row.step_minutes),
    )
    actors = (
        _ref("Practitioner", row.practitioner_id),
        *((_ref("Location", row.room_id),) if row.room_id else ()),
    )
    return Schedule(
        id=str(row.id),
        meta=meta(version_id(row.updated_at), row.updated_at),
        extension=(Extension(url=extension_url("availability"), extension=hours),),
        active=row.active,
        actor=actors,
        planning_horizon=Period(
            start=row.valid_from.isoformat(),
            end=row.valid_to.isoformat() if row.valid_to else None,
        ),
    )
