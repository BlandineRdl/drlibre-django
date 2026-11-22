import json

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import caller, reader
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.mappers.directory import extension_url
from drlibre.interfaces.fhir.params import (
    SearchQuery,
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
from drlibre.interfaces.fhir.routing import (
    bundle_response,
    entries_of,
    instants,
    missing,
    parse_id,
    reference,
    resource_response,
    token,
)
from drlibre.interfaces.fhir.schemas.audit_event import (
    AuditEvent,
    AuditEventAgent,
    AuditEventDetail,
    AuditEventEntity,
    AuditEventSource,
)
from drlibre.interfaces.fhir.schemas.common import Coding, Extension, Identifier, Reference
from drlibre.interfaces.fhir.version import meta
from drlibre.interop.application.ports.inbound import (
    AuditAction,
    AuditDetail,
    AuditEventFilter,
    AuditEventRow,
    Paging,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["audit-events"])

AUDIT_EVENT = declare(
    ResourceRules(
        type="AuditEvent",
        interactions=(Interaction.READ, Interaction.SEARCH),
        search=(
            SearchParam("agent", ParamType.REFERENCE),
            SearchParam("entity", ParamType.REFERENCE),
            SearchParam("entity-type", ParamType.TOKEN),
            SearchParam("action", ParamType.TOKEN),
            SearchParam("date", ParamType.DATE),
        ),
        sorts=("date",),
    )
)
# An entry never changes, so its version never does.
_VERSION = "1"
# The FHIR resource serving each audited entity type; a user is a Patient or a Practitioner.
_SERVED = {
    "appointment": "Appointment",
    "waitlist_entry": "Appointment",
    "booking_hold": "Appointment",
    "hospital": "Organization",
    "department": "Organization",
    "room": "Location",
    "appointment_type": "HealthcareService",
    "specialty": "CodeSystem",
    "clinician_profile": "PractitionerRole",
    "availability_rule": "Schedule",
    "notification": "Communication",
}
_CODES = frozenset(a.value for a in AuditAction)
_ENTITIES = ("Patient", "Practitioner", *sorted(set(_SERVED.values())))


def _user(user_id: Id, role: str | None) -> Reference:
    """A known user as their resource; a deleted one only by identifier."""
    if role is None:
        return Reference(identifier=Identifier(system=f"{base_url()}/user", value=str(user_id)))
    kind = "Patient" if role == "PATIENT" else "Practitioner"
    return Reference(reference=f"{kind}/{user_id}")


def _what(row: AuditEventRow) -> Reference | None:
    if row.entity_id is None:
        return None
    if row.entity_type == "user":
        return _user(row.entity_id, row.entity_role)
    if served := _SERVED.get(row.entity_type):
        return Reference(reference=f"{served}/{row.entity_id}")
    identifier = Identifier(system=f"{base_url()}/{row.entity_type}", value=str(row.entity_id))
    return Reference(identifier=identifier)


def _text(value: AuditDetail) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _agent(row: AuditEventRow) -> AuditEventAgent:
    if row.actor_id is None:
        return AuditEventAgent(name="système", requestor=False)
    return AuditEventAgent(who=_user(row.actor_id, row.actor_role), requestor=True)


def _resource(row: AuditEventRow) -> AuditEvent:
    """Spec §3.1: the entry's action, time, actor, entity and metadata, nothing more."""
    details = tuple(AuditEventDetail(type=k, value_string=_text(v)) for k, v in row.metadata)
    entity = AuditEventEntity(
        what=_what(row),
        type=Coding(system=f"{base_url()}/audit-entity-type", code=row.entity_type),
        detail=details or None,
    )
    correlation = Extension(url=extension_url("correlation-id"), value_string=row.correlation_id)
    return AuditEvent(
        id=str(row.id),
        meta=meta(_VERSION, row.at),
        extension=(correlation,) if row.correlation_id else None,
        type=Coding(system=f"{base_url()}/audit-domain", code=row.action.partition(".")[0]),
        subtype=(Coding(system=f"{base_url()}/audit-action", code=row.action),),
        action=AuditAction.of(row.action).value,
        recorded=row.at,
        agent=(_agent(row),),
        source=AuditEventSource(observer=Reference(display="DrLibre")),
        entity=(entity,),
    )


@router.get("/AuditEvent/{resource_id}")
def read_audit_event(request: HttpRequest, resource_id: str) -> HttpResponse:
    caller(request)
    refuse_undeclared(request.GET, frozenset())
    criteria = AuditEventFilter(ids=(parse_id(resource_id),))
    found = container().audit_events.events(criteria, reader(request)).items
    if not found:
        raise missing()
    return resource_response(_resource(found[0]), _VERSION)


def _actions(query: SearchQuery) -> tuple[AuditAction, ...]:
    raw = token(query, "action")
    codes = [c for c in (raw or "").split(",") if c]
    if unknown := [c for c in codes if c not in _CODES]:
        raise invalid_field("action", f"Valeur non prise en charge : {unknown[0]}.")
    return tuple(AuditAction(c) for c in codes)


def _entity(query: SearchQuery) -> Id | None:
    raw = query.first("entity")
    if raw is None:
        return None
    try:
        return Id.parse(reference_id("entity", raw, *_ENTITIES))
    except ValueError as error:
        raise invalid_field("entity", "Saisissez une référence <Type>/<id>.") from error


@router.get("/AuditEvent")
def search_audit_event(request: HttpRequest) -> HttpResponse:
    caller(request)
    query = search_query(request.GET, AUDIT_EVENT)
    at_from, at_before = instants(query, "date")
    criteria = AuditEventFilter(
        agent=reference(query, "agent", "Practitioner", "Patient"),
        entity=_entity(query),
        entity_type=token(query, "entity-type"),
        actions=_actions(query),
        at_from=at_from,
        at_before=at_before,
    )
    paging = Paging(count=query.count, page=query.page, descending=query.sort[:1] == ("-date",))
    page = container().audit_events.events(criteria, reader(request), paging)
    entries = entries_of(AUDIT_EVENT, page.items, _resource)
    return bundle_response(AUDIT_EVENT, query, page.total, entries)
