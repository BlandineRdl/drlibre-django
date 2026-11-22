from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import caller, reader
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.outcome import fhir_response
from drlibre.interfaces.fhir.params import refuse_undeclared, search_query
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
    missing,
    parse_id,
    read_body,
    reference,
    resource_response,
)
from drlibre.interfaces.fhir.schemas.appointment_response import AppointmentResponse
from drlibre.interfaces.fhir.schemas.common import Reference
from drlibre.interfaces.fhir.version import etag, meta, version_id
from drlibre.interop.application.ports.inbound import (
    AppointmentResponseFilter,
    AppointmentResponseRow,
    Paging,
    Reader,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["appointment-responses"])

APPOINTMENT_RESPONSE = declare(
    ResourceRules(
        type="AppointmentResponse",
        interactions=(Interaction.READ, Interaction.SEARCH, Interaction.CREATE),
        search=(
            SearchParam("patient", ParamType.REFERENCE),
            SearchParam("appointment", ParamType.REFERENCE),
        ),
    )
)
_ACCEPTED = "accepted"


def _version(row: AppointmentResponseRow) -> str:
    return version_id("response", row.updated_at)


def _resource(row: AppointmentResponseRow) -> AppointmentResponse:
    """Spec §15.3: the booked entry, accepted by its patient, names the appointment of its id."""
    return AppointmentResponse(
        id=str(row.id),
        meta=meta(_version(row), row.updated_at),
        appointment=Reference(reference=f"Appointment/{row.id}"),
        actor=Reference(reference=f"Patient/{row.patient_id}"),
        participant_status=_ACCEPTED,
    )


def _visible(response_id: Id, who: Reader) -> AppointmentResponseRow:
    """The response as the reader sees it; another forbidden, an absent one not_found."""
    queries = container().appointment_responses
    found = queries.responses(AppointmentResponseFilter(ids=(response_id,)), who).items
    if found:
        return found[0]
    if queries.exists(response_id):
        raise DomainError(ErrorCode.FORBIDDEN, "Cette réponse ne vous est pas ouverte.")
    raise missing()


@router.get("/AppointmentResponse/{resource_id}")
def read_appointment_response(request: HttpRequest, resource_id: str) -> HttpResponse:
    caller(request)
    refuse_undeclared(request.GET, frozenset())
    row = _visible(parse_id(resource_id), reader(request))
    return resource_response(_resource(row), _version(row))


@router.get("/AppointmentResponse")
def search_appointment_response(request: HttpRequest) -> HttpResponse:
    caller(request)
    query = search_query(request.GET, APPOINTMENT_RESPONSE)
    accepted = reference(query, "appointment", "Appointment")
    criteria = AppointmentResponseFilter(
        ids=(accepted,) if accepted else (), patient=reference(query, "patient", "Patient")
    )
    paging = Paging(count=query.count, page=query.page)
    page = container().appointment_responses.responses(criteria, reader(request), paging)
    entries = entries_of(APPOINTMENT_RESPONSE, page.items, _resource)
    return bundle_response(APPOINTMENT_RESPONSE, query, page.total, entries)


def _offer(resource: AppointmentResponse) -> Id:
    """The waitlist entry an `accepted` response names; the actor is the entry's patient."""
    if resource.participant_status != _ACCEPTED:
        raise invalid_field(
            "AppointmentResponse.participantStatus", "Seule une offre acceptée se crée."
        )
    path = "AppointmentResponse.appointment"
    kind, _, raw = (resource.appointment.reference or "").rpartition("/")
    try:
        if kind.rpartition("/")[2] != "Appointment":
            raise ValueError(kind)
        return Id.parse(raw)
    except ValueError as error:
        raise invalid_field(path, "Saisissez une référence Appointment/<id>.") from error


@router.post("/AppointmentResponse")
def create_appointment_response(request: HttpRequest) -> HttpResponse:
    """The use case `POST /api/v1/waitlist/{id}/accept` calls; the appointment keeps its id."""
    identity = caller(request)
    refuse_undeclared(request.GET, frozenset())
    entry_id = _offer(read_body(request, AppointmentResponse))
    container().accept_waitlist_offer.execute(actor_id=identity.user_id, entry_id=entry_id)
    row = _visible(entry_id, reader(request))
    model = _resource(row)
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=201)
    response["Location"] = f"{base_url()}/AppointmentResponse/{row.id}"
    response["ETag"] = etag(_version(row))
    return response
