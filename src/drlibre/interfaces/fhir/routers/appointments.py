from collections.abc import Iterable

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import caller, reader
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.diff import changes
from drlibre.interfaces.fhir.mappers import appointment as to
from drlibre.interfaces.fhir.mappers import directory
from drlibre.interfaces.fhir.mappers import patient as patients
from drlibre.interfaces.fhir.outcome import fhir_response
from drlibre.interfaces.fhir.params import (
    SearchQuery,
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
from drlibre.interfaces.fhir.routers.directory import LOCATION, PRACTITIONER
from drlibre.interfaces.fhir.routers.patients import PATIENT
from drlibre.interfaces.fhir.routing import (
    bundle_response,
    entries_of,
    instants,
    missing,
    parse_id,
    read_body,
    reference,
    resource_response,
    token,
)
from drlibre.interfaces.fhir.schemas.appointment import Appointment
from drlibre.interfaces.fhir.schemas.bundle import BundleEntry
from drlibre.interfaces.fhir.version import etag, expected_version
from drlibre.interop.application.ports.inbound import (
    AppointmentFilter,
    AppointmentKind,
    AppointmentRow,
    LocationFilter,
    Paging,
    PatientFilter,
    PractitionerFilter,
    Reader,
    RoleFilter,
    WriteTarget,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["appointments"])

APPOINTMENT = declare(
    ResourceRules(
        type="Appointment",
        interactions=(
            Interaction.READ,
            Interaction.SEARCH,
            Interaction.CREATE,
            Interaction.UPDATE,
        ),
        search=(
            SearchParam("patient", ParamType.REFERENCE),
            SearchParam("practitioner", ParamType.REFERENCE),
            SearchParam("location", ParamType.REFERENCE),
            SearchParam("status", ParamType.TOKEN),
            SearchParam("date", ParamType.DATE),
            SearchParam("service-type", ParamType.TOKEN),
        ),
        includes=("Appointment:patient", "Appointment:practitioner", "Appointment:location"),
        sorts=("date",),
    )
)


def _visible(appointment_id: Id, who: Reader) -> AppointmentRow:
    """The appointment as the reader sees it; another forbidden, an absent one not_found."""
    queries = container().interop_appointments
    found = queries.appointments(AppointmentFilter(ids=(appointment_id,)), who).items
    if found:
        return found[0]
    if queries.exists(appointment_id):
        raise DomainError(ErrorCode.FORBIDDEN, "Ce rendez-vous ne vous est pas ouvert.")
    raise missing()


@router.get("/Appointment/{resource_id}")
def read_appointment(request: HttpRequest, resource_id: str) -> HttpResponse:
    caller(request)
    refuse_undeclared(request.GET, frozenset())
    row = _visible(parse_id(resource_id), reader(request))
    return resource_response(to.appointment(row), to.version_of(row))


def _statuses(query: SearchQuery) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for raw in (v for value in query.values("status") for v in value.split(",") if v):
        found = to.statuses_of(raw)
        if not found:
            raise invalid_field("status", f"Valeur non prise en charge : {raw}.")
        pairs += found
    return tuple(pairs)


def _service_type(query: SearchQuery) -> Id | None:
    raw = token(query, "service-type")
    if raw is None:
        return None
    try:
        return Id.parse(raw)
    except ValueError as error:
        raise invalid_field("service-type", "Saisissez l'id d'un HealthcareService.") from error


def _ids(found: Iterable[Id | None]) -> tuple[Id, ...]:
    return tuple(dict.fromkeys(i for i in found if i is not None))


def _included(
    rows: tuple[AppointmentRow, ...], query: SearchQuery, who: Reader
) -> list[BundleEntry]:
    entries: list[BundleEntry] = []
    if "Appointment:patient" in query.includes:
        found = _ids(r.patient_id for r in rows)
        page = container().patient_queries.patients(PatientFilter(ids=found), who)
        entries += entries_of(PATIENT, page.items, patients.patient, include=True)
    if "Appointment:practitioner" in query.includes:
        found = _ids(r.practitioner_id for r in rows)
        listed = container().directory_queries.practitioners(PractitionerFilter(ids=found), who)
        entries += entries_of(PRACTITIONER, listed.items, directory.practitioner, include=True)
    if "Appointment:location" in query.includes:
        found = _ids(r.room_id for r in rows)
        rooms = container().directory_queries.locations(LocationFilter(ids=found), who)
        entries += entries_of(LOCATION, rooms.items, directory.location, include=True)
    return entries


@router.get("/Appointment")
def search_appointment(request: HttpRequest) -> HttpResponse:
    caller(request)
    query = search_query(request.GET, APPOINTMENT)
    who = reader(request)
    start_from, start_before = instants(query, "date")
    criteria = AppointmentFilter(
        patient=reference(query, "patient", "Patient"),
        practitioner=reference(query, "practitioner", "Practitioner"),
        room=reference(query, "location", "Location"),
        appointment_type=_service_type(query),
        statuses=_statuses(query),
        start_from=start_from,
        start_before=start_before,
    )
    paging = Paging(count=query.count, page=query.page, descending=query.sort[:1] == ("-date",))
    page = container().interop_appointments.appointments(criteria, who, paging)
    entries = entries_of(APPOINTMENT, page.items, to.appointment)
    entries += _included(page.items, query, who)
    return bundle_response(APPOINTMENT, query, page.total, entries)


def _profile_seen(practitioner_id: Id, who: Reader) -> Id | None:
    """The clinician profile of a practitioner user the reader sees, else None."""
    roles = container().directory_queries.roles(RoleFilter(practitioner=practitioner_id), who)
    return next((r.id for r in roles.items if not r.is_admin), None)


def _profile_of(practitioner_id: Id | None, who: Reader) -> Id | None:
    """The clinician profile of a practitioner user; one the reader cannot see is not_found."""
    if practitioner_id is None:
        return None
    found = _profile_seen(practitioner_id, who)
    if found is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
    return found


def _preferred(practitioner_id: Id | None, who: Reader) -> Id | None:
    """An unseen practitioner passes as is: the use case judges the caller before not_found."""
    if practitioner_id is None:
        return None
    return _profile_seen(practitioner_id, who) or practitioner_id


def _created(appointment_id: Id, who: Reader) -> HttpResponse:
    row = _visible(appointment_id, who)
    model = to.appointment(row)
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=201)
    response["Location"] = f"{base_url()}/Appointment/{appointment_id}"
    response["ETag"] = etag(to.version_of(row))
    return response


def _join(actor_id: Id, resource: Appointment, who: Reader) -> HttpResponse:
    """The use case `POST /api/v1/waitlist` calls; the patient is named by id, not email."""
    asked = to.waitlist_request(resource)
    entry = container().join_waitlist.execute(
        actor_id=actor_id,
        appointment_type_id=asked.appointment_type_id,
        clinician_id=_preferred(asked.practitioner_id, who),
        from_date=asked.from_date,
        to_date=asked.to_date,
        patient_email=None,
        patient_id=asked.patient_id,
    )
    return _created(entry.id, who)


@router.post("/Appointment")
def create_appointment(request: HttpRequest) -> HttpResponse:
    identity = caller(request)
    refuse_undeclared(request.GET, frozenset())
    resource = read_body(request, Appointment)
    who = reader(request)
    if resource.status == "waitlist":
        return _join(identity.user_id, resource, who)
    asked = to.booking_request(resource)
    named = _profile_of(asked.practitioner_id, who)
    if asked.profile_id is not None and named not in (None, asked.profile_id):
        raise invalid_field("Appointment.participant", "Le praticien n'est pas celui du créneau.")
    booked = container().book_appointment_as_caller.execute(
        actor_id=identity.user_id,
        appointment_type_id=asked.appointment_type_id,
        start=asked.start,
        clinician_id=asked.profile_id or named,
        patient_id=asked.patient_id,
        room_id=asked.room_id,
    )
    return _created(booked.id, who)


def _apply(intent: to.Intent, actor_id: Id, appointment_id: Id, incoming: Appointment) -> None:
    """The use case `POST /api/v1/appointments/{id}/…` calls for the same intent."""
    c, ids = container(), {"actor_id": actor_id, "appointment_id": appointment_id}
    match intent:
        case to.Intent.RESCHEDULE:
            c.reschedule_appointment.execute(start=to.start_of(incoming), **ids)
        case to.Intent.CANCEL:
            c.cancel_appointment.execute(reason=to.cancellation_reason(incoming), **ids)
        case to.Intent.CHECK_IN:
            c.check_in_appointment.execute(**ids)
        case to.Intent.COMPLETE:
            c.complete_appointment.execute(**ids)
        case to.Intent.NO_SHOW:
            c.mark_no_show.execute(**ids)
        case to.Intent.NOTES:
            c.write_clinical_notes.execute(text=incoming.comment or "", **ids)


@router.put("/Appointment/{resource_id}")
def update_appointment(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    who = reader(request)
    appointment_id = parse_id(resource_id)
    row = _visible(appointment_id, who)
    incoming = read_body(request, Appointment)
    if incoming.id not in (None, resource_id):
        raise invalid_field("Appointment.id", "L'id doit être celui de l'adresse.")
    clinician_id, patient_id = row.clinician_id, row.patient_id
    # Waitlist entries and holds change through their own interactions, if any.
    if row.kind is not AppointmentKind.APPOINTMENT or clinician_id is None or patient_id is None:
        raise to.refused_transition(row)

    def write() -> None:
        current = _visible(appointment_id, who)
        changed = changes(
            to.fields(to.appointment(current)), to.fields(incoming), writable=to.WRITABLE
        )
        if (intent := to.intent(current, changed, incoming)) is not None:
            _apply(intent, identity.user_id, appointment_id, incoming)

    container().conditional_writes.run(
        target=WriteTarget.appointment(
            clinician_id=clinician_id, patient_id=patient_id, appointment_id=row.id
        ),
        expected=expected_version(request.headers.get("If-Match")),
        current=lambda: to.version_of(_visible(appointment_id, who)),
        write=write,
    )
    row = _visible(appointment_id, who)
    return resource_response(to.appointment(row), to.version_of(row))
