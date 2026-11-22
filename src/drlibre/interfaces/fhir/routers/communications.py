from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import caller, reader
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.diff import changes
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
    instants,
    missing,
    parse_id,
    read_body,
    reference,
    resource_response,
    token,
)
from drlibre.interfaces.fhir.schemas.common import CodeableConcept, Coding, Reference
from drlibre.interfaces.fhir.schemas.communication import Communication, CommunicationPayload
from drlibre.interfaces.fhir.version import expected_version, meta, version_id
from drlibre.interop.application.ports.inbound import (
    CommunicationFilter,
    CommunicationRow,
    Paging,
    Reader,
    WriteTarget,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["communications"])

COMMUNICATION = declare(
    ResourceRules(
        type="Communication",
        interactions=(Interaction.READ, Interaction.SEARCH, Interaction.UPDATE),
        search=(
            SearchParam("recipient", ParamType.REFERENCE),
            SearchParam("category", ParamType.TOKEN),
            SearchParam("sent", ParamType.DATE),
        ),
        sorts=("sent",),
    )
)
_RECEIVED = "Communication.received"


def _version(row: CommunicationRow) -> str:
    return version_id("communication", row.updated_at)


def _recipient(row: CommunicationRow) -> Reference:
    kind = "Patient" if row.recipient_role == "PATIENT" else "Practitioner"
    return Reference(reference=f"{kind}/{row.recipient_id}")


def _resource(row: CommunicationRow) -> Communication:
    """Spec §11: the kind as category, the title as topic, the body as payload."""
    category = Coding(system=f"{base_url()}/notification-kind", code=row.kind)
    about = (Reference(reference=f"Appointment/{row.appointment_id}"),)
    return Communication(
        id=str(row.id),
        meta=meta(_version(row), row.updated_at),
        status="completed",
        category=(CodeableConcept(coding=(category,)),),
        recipient=(_recipient(row),),
        topic=CodeableConcept(text=row.title),
        about=about if row.appointment_id else None,
        payload=(CommunicationPayload(content_string=row.body),),
        sent=row.sent,
        received=row.received,
    )


def _fields(resource: Communication) -> dict[str, object]:
    """The elements an update is compared on, by FHIR path; `id` and `meta` are not."""
    dumped = resource.model_dump(mode="json", by_alias=True, exclude_none=True)
    paths = ("status", "category", "recipient", "topic", "about", "payload", "sent")
    return {f"Communication.{p}": dumped.get(p) for p in paths} | {_RECEIVED: resource.received}


def _visible(communication_id: str, who: Reader) -> CommunicationRow:
    """The notification as its recipient reads it; another's forbidden, an absent one not_found."""
    found_id = parse_id(communication_id)
    queries = container().communications
    found = queries.communications(CommunicationFilter(ids=(found_id,)), who).items
    if found:
        return found[0]
    if queries.exists(found_id):
        raise DomainError(ErrorCode.FORBIDDEN, "Cette notification n'est pas la vôtre.")
    raise missing()


@router.get("/Communication/{resource_id}")
def read_communication(request: HttpRequest, resource_id: str) -> HttpResponse:
    caller(request)
    refuse_undeclared(request.GET, frozenset())
    row = _visible(resource_id, reader(request))
    return resource_response(_resource(row), _version(row))


@router.get("/Communication")
def search_communication(request: HttpRequest) -> HttpResponse:
    caller(request)
    query = search_query(request.GET, COMMUNICATION)
    sent_from, sent_before = instants(query, "sent")
    criteria = CommunicationFilter(
        recipient=reference(query, "recipient", "Patient", "Practitioner"),
        category=token(query, "category"),
        sent_from=sent_from,
        sent_before=sent_before,
    )
    paging = Paging(count=query.count, page=query.page, descending=query.sort[:1] == ("-sent",))
    page = container().communications.communications(criteria, reader(request), paging)
    entries = entries_of(COMMUNICATION, page.items, _resource)
    return bundle_response(COMMUNICATION, query, page.total, entries)


@router.put("/Communication/{resource_id}")
def update_communication(request: HttpRequest, resource_id: str) -> HttpResponse:
    """`received` filled is the portal's « Marquer comme lu »; the server keeps its own time."""
    identity = caller(request)
    who = reader(request)
    row = _visible(resource_id, who)
    incoming = read_body(request, Communication)
    if incoming.id not in (None, resource_id):
        raise invalid_field("Communication.id", "L'id doit être celui de l'adresse.")

    def write() -> None:
        current = _visible(resource_id, who)
        # Once read, a notification stays read: `received` is writable while empty only.
        writable = frozenset({_RECEIVED}) if current.received is None else frozenset()
        if changes(_fields(_resource(current)), _fields(incoming), writable=writable):
            container().mark_notification_read.execute(
                user_id=identity.user_id, notification_id=current.id
            )

    container().conditional_writes.run(
        target=WriteTarget.user(user_id=row.recipient_id),
        expected=expected_version(request.headers.get("If-Match")),
        current=lambda: _version(_visible(resource_id, who)),
        write=write,
    )
    row = _visible(resource_id, who)
    return resource_response(_resource(row), _version(row))
