"""Written resources as the `fields` the console's use cases take; computed elements are ignored."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.mappers.directory import (
    ORGANIZATION_TYPE,
    PHYSICAL_TYPE,
    PRODUCT_CODE,
    UNAVAILABLE,
    extension_url,
)
from drlibre.interfaces.fhir.schemas.common import (
    Address,
    CodeableConcept,
    ContactPoint,
    Extension,
    HumanName,
    Identifier,
    Reference,
)
from drlibre.interfaces.fhir.schemas.directory import (
    CodeSystem,
    HealthcareService,
    Location,
    NotAvailable,
    Organization,
    Practitioner,
    PractitionerRole,
)
from drlibre.interfaces.fhir.schemas.patient import Patient
from drlibre.interop.application.ports.inbound import TimeOffRow
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

type Fields = dict[str, str]
TEMPORARY_PASSWORD = "temporary-password"  # noqa: S105  # nosec B105
ROLE = "role"


def _flag(value: bool | None) -> str:
    return "on" if value else ""


def _extensions(found: Sequence[Extension] | None, name: str) -> list[Extension]:
    return [e for e in found or () if e.url == extension_url(name)]


def _string(found: Sequence[Extension] | None, name: str) -> str:
    values = [e.value_string or e.value_code or "" for e in _extensions(found, name)]
    return values[0] if values else ""


def _number(found: Sequence[Extension] | None, name: str) -> str:
    values = [e.value_integer for e in _extensions(found, name) if e.value_integer is not None]
    return str(values[0]) if values else ""


def _boolean(found: Sequence[Extension] | None, name: str) -> str:
    return _flag(any(e.value_boolean for e in _extensions(found, name)))


def _code(identifiers: Sequence[Identifier] | None) -> str:
    values = [i.value for i in identifiers or () if i.system == PRODUCT_CODE]
    return values[0] if values else ""


def reference_id(found: Reference | None, resource_type: str) -> str:
    """The id a `<type>/<id>` reference names, empty when it names another type or nothing."""
    raw = (found.reference if found else None) or ""
    prefix = f"{resource_type}/"
    return raw.removeprefix(prefix) if raw.startswith(prefix) else ""


def _coded(concepts: Sequence[CodeableConcept] | None, system: str) -> str | None:
    codes = [c.code for k in concepts or () for c in k.coding or () if c.system == system]
    return codes[0] if codes else None


def organization_kind(resource: Organization) -> str | None:
    """`prov` for a hospital, `dept` for a department."""
    return _coded(resource.type, ORGANIZATION_TYPE)


def location_kind(resource: Location) -> str | None:
    return _coded((resource.physical_type,), PHYSICAL_TYPE)


def _phone(telecom: Sequence[ContactPoint] | None) -> str:
    return next((c.value for c in telecom or () if c.system == "phone"), "")


def _email(telecom: Sequence[ContactPoint] | None) -> str:
    return next((c.value for c in telecom or () if c.system == "email"), "")


def _decimal(found: Sequence[Extension], name: str) -> str:
    values = [e.value_decimal for e in found if e.url == name and e.value_decimal is not None]
    return str(values[0]) if values else ""


def hospital_fields(resource: Organization) -> Fields:
    address = resource.address[0] if resource.address else Address()
    position = [p for e in _extensions(resource.extension, "position") for p in e.extension or ()]
    return {
        "name": resource.name,
        "code": _code(resource.identifier),
        "description": _string(resource.extension, "description"),
        "street": (address.line or ("",))[0],
        "postal_code": address.postal_code or "",
        "city": address.city or "",
        "country": address.country or "",
        "phone": _phone(resource.telecom),
        "time_zone": _string(resource.extension, "time-zone"),
        "latitude": _decimal(position, "latitude"),
        "longitude": _decimal(position, "longitude"),
        "active": _flag(resource.active),
    }


def department_fields(resource: Organization) -> Fields:
    return {
        "hospital_id": reference_id(resource.part_of, "Organization"),
        "name": resource.name,
        "code": _code(resource.identifier),
        "description": _string(resource.extension, "description"),
    }


def room_fields(resource: Location) -> Fields:
    equipment = [e.value_string or "" for e in _extensions(resource.extension, "equipment")]
    return {
        "department_id": reference_id(resource.managing_organization, "Organization"),
        "name": resource.name,
        "code": _code(resource.identifier),
        "floor": _string(resource.extension, "floor"),
        "capacity": _number(resource.extension, "capacity"),
        "equipment": ",".join(equipment),
        "active": _flag(resource.status == "active"),
    }


def type_fields(resource: HealthcareService) -> Fields:
    found = resource.extension
    return {
        "department_id": reference_id(resource.provided_by, "Organization"),
        "name": resource.name,
        "code": _code(resource.identifier),
        "duration_minutes": _number(found, "duration-minutes"),
        "buffer_minutes": _number(found, "buffer-minutes"),
        "colour": _string(found, "colour"),
        "needs_room": _boolean(found, "needs-room"),
        "bookable_online": _boolean(found, "bookable-online"),
        "active": _flag(resource.active),
    }


def specialty_fields(resource: CodeSystem) -> Fields:
    """A specialty is one code system with a single concept: its code; the title names it."""
    if len(resource.concept) != 1:
        raise invalid_field("CodeSystem.concept", "Une spécialité porte un seul concept.")
    return {
        "name": resource.title,
        "code": resource.concept[0].code,
        "active": _flag(resource.status == "active"),
    }


def _specialty_id(resource: PractitionerRole) -> str:
    prefix = f"{base_url()}/CodeSystem/"
    systems = [c.system or "" for k in resource.specialty or () for c in k.coding or ()]
    return next((s.removeprefix(prefix) for s in systems if s.startswith(prefix)), "")


def profile_fields(resource: PractitionerRole, *, room_id: str, title: str) -> Fields:
    """`title` is the current one unless the role's `title` extension names another."""
    return {
        "department_id": reference_id(resource.organization, "Organization"),
        "specialty_id": _specialty_id(resource),
        "default_room_id": room_id,
        "title": _string(resource.extension, "title") or title,
        "bio": _string(resource.extension, "bio"),
        "weight": _number(resource.extension, "round-robin-weight"),
    }


def role_paths(resource: PractitionerRole) -> dict[str, object]:
    """What an admin update may not change: the clinician, and the hours they keep themselves."""
    return {
        "PractitionerRole.practitioner": reference_id(resource.practitioner, "Practitioner"),
        "PractitionerRole.availableTime": tuple(
            a.model_dump() for a in resource.available_time or ()
        ),
        "PractitionerRole.notAvailable": tuple(
            n.model_dump() for n in resource.not_available or ()
        ),
    }


def own_role_paths(resource: PractitionerRole) -> dict[str, object]:
    """Every element but `notAvailable`, the only one its clinician changes."""
    dumped = resource.model_dump(
        by_alias=True, exclude_none=True, exclude={"id", "meta", "not_available"}
    )
    return {f"PractitionerRole.{name}": value for name, value in dumped.items()}


@dataclass(frozen=True, slots=True)
class TimeOffChanges:
    """A `notAvailable` update: the time offs it drops, then the periods it adds."""

    removed: tuple[Id, ...]
    added: tuple[Fields, ...]


def _instant(raw: str | None, path: str) -> datetime:
    try:
        found = datetime.fromisoformat(raw or "")
    except ValueError:
        found = None
    if found is None or found.tzinfo is None:
        raise invalid_field(path, "Saisissez une date et une heure avec fuseau.")
    return found


def _local(at: datetime, zone: ZoneInfo) -> str:
    return at.astimezone(zone).replace(tzinfo=None).isoformat()


def time_off_changes(
    current: Sequence[TimeOffRow], incoming: Sequence[NotAvailable], zone: ZoneInfo
) -> TimeOffChanges:
    """Periods matched one for one on start, end and description; the rest is dropped or added."""
    kept = list(current)
    added: list[Fields] = []
    for period in incoming:
        start = _instant(period.during.start, "PractitionerRole.notAvailable.during.start")
        end = _instant(period.during.end, "PractitionerRole.notAvailable.during.end")
        key = (start, end, period.description)
        same = next((o for o in kept if (o.start, o.end, o.reason or UNAVAILABLE) == key), None)
        if same is not None:
            kept.remove(same)
            continue
        reason = "" if period.description == UNAVAILABLE else period.description
        added.append({"start": _local(start, zone), "end": _local(end, zone), "reason": reason})
    return TimeOffChanges(tuple(o.id for o in kept), tuple(added))


@dataclass(frozen=True, slots=True)
class UserValues:
    """What `SaveUser` takes from a `Practitioner` or `Patient`; the password is write-only."""

    full_name: str
    email: str
    active: bool
    temporary_password: str
    role: str | None


def _name(names: Sequence[HumanName] | None) -> str:
    return names[0].text if names else ""


def user_values(resource: Practitioner | Patient) -> UserValues:
    found = resource.extension
    return UserValues(
        full_name=_name(resource.name),
        email=_email(resource.telecom),
        active=resource.active is not False,
        temporary_password=_string(found, TEMPORARY_PASSWORD),
        role=_string(found, ROLE) or None,
    )


def practitioner_paths(resource: Practitioner) -> dict[str, object]:
    """The elements an admin update is compared on; write-only extensions are not among them."""
    name = resource.name[0] if resource.name else None
    return {
        "Practitioner.active": resource.active,
        "Practitioner.name.text": name.text if name else None,
        "Practitioner.name.prefix": name.prefix if name else None,
        "Practitioner.telecom.email": _email(resource.telecom),
        "Practitioner.telecom.phone": _phone(resource.telecom),
    }


# The user screen of the console edits these; a practitioner's title belongs to their profile.
PRACTITIONER_WRITABLE = frozenset(
    {"Practitioner.active", "Practitioner.name.text", "Practitioner.telecom.email"}
)
PATIENT_WRITABLE = frozenset({"Patient.active", "Patient.name", "Patient.telecom.email"})
