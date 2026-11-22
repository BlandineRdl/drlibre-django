from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import reader
from drlibre.interfaces.fhir.bundle import base_url, entry
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
from drlibre.interfaces.fhir.routers.directory import (
    SCHEDULE,
    _bundle,
    _entries,
    _json,
    _missing,
    _ref,
    _resource,
    _token,
)
from drlibre.interfaces.fhir.schemas.common import CodeableConcept, Coding, Meta, Reference
from drlibre.interfaces.fhir.schemas.slot import Slot
from drlibre.interfaces.fhir.slot_id import SlotKey, slot_id, slot_key
from drlibre.interfaces.fhir.version import version_id
from drlibre.interop.application.ports.inbound import Reader, ScheduleFilter, ScheduleRow
from drlibre.scheduling.application.ports.inbound import FREE_ONLY, SlotState, SlotStatus
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["slots"])

SLOT = declare(
    ResourceRules(
        type="Slot",
        interactions=(Interaction.READ, Interaction.SEARCH),
        search=(
            SearchParam("schedule", ParamType.REFERENCE),
            SearchParam("schedule.actor", ParamType.REFERENCE),
            SearchParam("service-type", ParamType.TOKEN),
            SearchParam("start", ParamType.DATE),
            SearchParam("status", ParamType.TOKEN),
        ),
        includes=("Slot:schedule",),
        sorts=("start",),
    )
)
_INSTANT = "Saisissez un instant ISO 8601 avec son fuseau."
_AFTER = timedelta(microseconds=1)


def _slot(state: SlotState, kind: Id, rule: ScheduleRow | None) -> Slot:
    """A computed slot: its version fingerprints its fields, its last update is its rule's."""
    found = slot_id(SlotKey(state.clinician_id, kind, state.start))
    service = Coding(system=f"{base_url()}/HealthcareService", code=str(kind))
    return Slot(
        id=found,
        meta=Meta(
            version_id=version_id(found, state.rule_id, state.end, state.status),
            last_updated=rule.updated_at if rule else None,
        ),
        service_type=(CodeableConcept(coding=(service,)),),
        schedule=Reference(reference=f"Schedule/{state.rule_id}"),
        status=state.status,
        start=state.start.isoformat(),
        end=state.end.isoformat(),
    )


def _rules(ids: Sequence[Id], who: Reader) -> dict[Id, ScheduleRow]:
    if not ids:
        return {}
    rows = container().directory_queries.schedules(ScheduleFilter(ids=tuple(ids)), who).items
    return {r.id: r for r in rows}


@router.get("/Slot/{resource_id}")
def read_slot(request: HttpRequest, resource_id: str) -> HttpResponse:
    refuse_undeclared(request.GET, frozenset())
    key = slot_key(resource_id)
    if key is None:
        raise _missing()
    who = reader(request)
    state = container().read_slot_state.execute(
        appointment_type_id=key.appointment_type_id,
        clinician_id=key.clinician_id,
        start=key.start,
        staff=who.is_staff,
    )
    if state is None:
        raise _missing()
    model = _slot(state, key.appointment_type_id, _rules((state.rule_id,), who).get(state.rule_id))
    return _resource(model, model.meta.version_id or "")


def _range(query: SearchQuery) -> tuple[datetime, datetime]:
    """The `start` bounds: a slot lies from the ge/gt instant to the le/lt one."""
    start = end = None
    for raw in query.values("start"):
        bound = date_bound("start", raw)
        if not isinstance(bound.value, datetime):
            raise invalid_field("start", _INSTANT)
        if bound.prefix in (Prefix.GE, Prefix.GT):
            start = bound.value + (_AFTER if bound.prefix is Prefix.GT else timedelta())
        elif bound.prefix in (Prefix.LE, Prefix.LT):
            end = bound.value
    if start is None or end is None:
        raise invalid_field("start", "Bornez la période par start=ge… et start=lt….")
    return start, end


def _service_type(query: SearchQuery) -> Id:
    raw = _token(query, "service-type")
    if raw is None:
        raise invalid_field("service-type", "Précisez le type de RDV.")
    try:
        return Id.parse(raw)
    except ValueError as error:
        raise invalid_field("service-type", "Saisissez l'id d'un HealthcareService.") from error


def _statuses(query: SearchQuery) -> frozenset[SlotStatus]:
    raw = [v for value in query.values("status") for v in value.split(",") if v]
    known = {s.value: s for s in SlotStatus}
    for value in raw:
        if value not in known:
            raise invalid_field("status", f"Valeur non prise en charge : {value}.")
    return frozenset(known[v] for v in raw) or FREE_ONLY


def _schedules(query: SearchQuery, who: Reader) -> tuple[ScheduleRow, ...] | None:
    """The rules `schedule` and `schedule.actor` narrow to, or None when neither is given."""
    rule = _ref(query, "schedule", "Schedule")
    actor = _ref(query, "schedule.actor", "Practitioner")
    if rule is None and actor is None:
        return None
    criteria = ScheduleFilter(ids=(rule,) if rule else (), actor=actor)
    return tuple(container().directory_queries.schedules(criteria, who).items)


def _states(query: SearchQuery, who: Reader, kind: Id) -> list[SlotState]:
    start, end = _range(query)
    statuses = _statuses(query)
    narrowed = _schedules(query, who)
    profiles = (None,) if narrowed is None else tuple(dict.fromkeys(r.role_id for r in narrowed))
    found: list[SlotState] = []
    for profile in profiles:
        found += container().find_slot_states.execute(
            appointment_type_id=kind,
            clinician_id=profile,
            start=start,
            end=end,
            statuses=statuses,
            staff=who.is_staff,
        )
    if narrowed is not None:
        rules = {r.id for r in narrowed}
        found = [s for s in found if s.rule_id in rules]
    found.sort(key=lambda s: (s.start, str(s.clinician_id)), reverse=query.sort[:1] == ("-start",))
    return found


@router.get("/Slot")
def search_slot(request: HttpRequest) -> HttpResponse:
    query = search_query(request.GET, SLOT)
    who = reader(request)
    kind = _service_type(query)
    states = _states(query, who, kind)
    page = states[(query.page - 1) * query.count : query.page * query.count]
    rules: Mapping[Id, ScheduleRow] = _rules(tuple(dict.fromkeys(s.rule_id for s in page)), who)
    entries = [
        entry(SLOT.type, model.id, _json(model))
        for model in (_slot(s, kind, rules.get(s.rule_id)) for s in page)
    ]
    if "Slot:schedule" in query.includes:
        entries += _entries(SCHEDULE, tuple(rules.values()), to.schedule, include=True)
    return _bundle(SLOT, query, len(states), entries)
