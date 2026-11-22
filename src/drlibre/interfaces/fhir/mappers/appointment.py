from dataclasses import dataclass
from datetime import datetime

from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.mappers.directory import extension_url
from drlibre.interfaces.fhir.schemas.appointment import Appointment, Participant
from drlibre.interfaces.fhir.schemas.common import (
    CodeableConcept,
    Coding,
    Extension,
    Period,
    Reference,
)
from drlibre.interfaces.fhir.slot_id import slot_key
from drlibre.interfaces.fhir.version import meta, version_id
from drlibre.interop.application.ports.inbound import HELD, AppointmentKind, AppointmentRow
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

_A, _W, _H = AppointmentKind.APPOINTMENT, AppointmentKind.WAITLIST, AppointmentKind.HOLD
# Spec §15.3: each record's own status as an `Appointment.status`.
STATUSES: dict[tuple[str, str], str] = {
    (_A, "BOOKED"): "booked",
    (_A, "CHECKED_IN"): "checked-in",
    (_A, "COMPLETED"): "fulfilled",
    (_A, "CANCELLED"): "cancelled",
    (_A, "NO_SHOW"): "noshow",
    (_W, "WAITING"): "waitlist",
    (_W, "OFFERED"): "proposed",
    (_W, "EXPIRED"): "cancelled",
    (_H, HELD): "pending",
}
SOURCE = "source"
_REFUSED_ON_CREATE = {
    "reason_code": "Appointment.reasonCode",
    "comment": "Appointment.comment",
}


def statuses_of(status: str) -> tuple[tuple[str, str], ...]:
    """The records whose status maps to a FHIR one; none for a status the server never gives."""
    return tuple(key for key, value in STATUSES.items() if value == status)


def service_type(appointment_type_id: Id) -> CodeableConcept:
    coding = Coding(system=f"{base_url()}/HealthcareService", code=str(appointment_type_id))
    return CodeableConcept(coding=(coding,))


def version_of(row: AppointmentRow) -> str:
    return version_id(row.kind, row.updated_at)


def _actor(resource_type: str, found: Id | None) -> tuple[Participant, ...]:
    return (Participant(actor=Reference(reference=f"{resource_type}/{found}")),) if found else ()


def _instant(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def appointment(row: AppointmentRow) -> Appointment:
    """The resource of a row; its notes are already left out for anyone but its clinician."""
    cancelled = row.kind is _A and row.status == "CANCELLED"
    window = Period(start=_instant(row.earliest), end=_instant(row.latest))
    return Appointment(
        id=str(row.id),
        meta=meta(version_of(row), row.updated_at),
        extension=(Extension(url=extension_url(SOURCE), value_code=row.source),)
        if row.source
        else None,
        status=STATUSES[(row.kind, row.status)],
        cancelation_reason=CodeableConcept(text=row.cancellation_reason)
        if cancelled and row.cancellation_reason
        else None,
        service_type=(service_type(row.appointment_type_id),),
        reason_code=(CodeableConcept(text=row.reason),) if row.reason else None,
        start=_instant(row.start),
        end=_instant(row.end),
        comment=row.clinical_notes,
        participant=(
            *_actor("Patient", row.patient_id),
            *_actor("Practitioner", row.practitioner_id),
            *_actor("Location", row.room_id),
        ),
        requested_period=(window,) if row.earliest else None,
    )


@dataclass(frozen=True, slots=True)
class BookingRequest:
    """What a created `Appointment` asks: a clinician by profile (slot) or by user (participant)."""

    appointment_type_id: Id
    start: datetime
    profile_id: Id | None
    practitioner_id: Id | None
    patient_id: Id | None
    room_id: Id | None


def _references(resource: Appointment, resource_type: str) -> list[Id]:
    found = []
    for participant in resource.participant or ():
        reference = participant.actor.reference if participant.actor else None
        kind, _, raw = (reference or "").rpartition("/")
        if kind.rpartition("/")[2] == resource_type:
            try:
                found.append(Id.parse(raw))
            except ValueError as error:
                raise invalid_field(
                    "Appointment.participant", f"Saisissez une référence {resource_type}/<id>."
                ) from error
    if len(found) > 1:
        raise invalid_field("Appointment.participant", f"Un seul {resource_type} par RDV.")
    return found


def _one(resource: Appointment, resource_type: str) -> Id | None:
    found = _references(resource, resource_type)
    return found[0] if found else None


def _type_of(resource: Appointment) -> Id | None:
    codes = [c.code for s in resource.service_type or () for c in s.coding or () if c.code]
    if not codes:
        return None
    try:
        return Id.parse(codes[0].rpartition("/")[2])
    except ValueError as error:
        raise invalid_field(
            "Appointment.serviceType", "Saisissez l'id d'un HealthcareService."
        ) from error


def _start_of(resource: Appointment) -> datetime | None:
    if resource.start is None:
        return None
    try:
        start = datetime.fromisoformat(resource.start)
    except ValueError:
        start = None
    if start is None or start.tzinfo is None:
        raise invalid_field("Appointment.start", "Saisissez un instant ISO 8601 avec son fuseau.")
    return start


def booking_request(resource: Appointment) -> BookingRequest:
    """A `proposed` appointment as a booking; `end`, `meta` and the source are the server's."""
    if resource.status != "proposed":
        raise invalid_field("Appointment.status", "Créez un RDV au statut proposed.")
    for name, path in _REFUSED_ON_CREATE.items():
        if getattr(resource, name) is not None:
            raise invalid_field(path, "Ce champ ne se saisit pas à la réservation.")
    kind, start, profile = _type_of(resource), _start_of(resource), None
    slots = resource.slot or ()
    if len(slots) > 1:
        raise invalid_field("Appointment.slot", "Un seul créneau par RDV.")
    if slots:
        key = slot_key((slots[0].reference or "").rpartition("/")[2])
        if key is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Créneau introuvable.")
        if kind not in (None, key.appointment_type_id) or start not in (None, key.start):
            raise invalid_field("Appointment.slot", "Ce créneau ne correspond pas au RDV.")
        kind, start, profile = key.appointment_type_id, key.start, key.clinician_id
    if kind is None:
        raise invalid_field("Appointment.serviceType", "Précisez le type de RDV.")
    if start is None:
        raise invalid_field("Appointment.start", "Précisez le début ou le créneau.")
    return BookingRequest(
        appointment_type_id=kind,
        start=start,
        profile_id=profile,
        practitioner_id=_one(resource, "Practitioner"),
        patient_id=_one(resource, "Patient"),
        room_id=_one(resource, "Location"),
    )
