from datetime import date, datetime

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.interfaces.fhir.access import caller, reader
from drlibre.interfaces.fhir.diff import changes
from drlibre.interfaces.fhir.mappers import patient as to
from drlibre.interfaces.fhir.params import Prefix, date_bound, refuse_undeclared, search_query
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
    paging_of,
    parse_id,
    read_body,
    resource_response,
    token,
)
from drlibre.interfaces.fhir.schemas.patient import Patient
from drlibre.interfaces.fhir.version import expected_version
from drlibre.interop.application.ports.inbound import (
    PatientFilter,
    PatientRow,
    Reader,
    WriteTarget,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["patients"])

PATIENT = declare(
    ResourceRules(
        type="Patient",
        interactions=(Interaction.READ, Interaction.SEARCH, Interaction.UPDATE),
        search=(
            SearchParam("name", ParamType.STRING),
            SearchParam("email", ParamType.TOKEN),
            SearchParam("phone", ParamType.TOKEN),
            SearchParam("birthdate", ParamType.DATE),
        ),
        sorts=("name",),
    )
)
# The profile screen lets a patient change these two, nothing else.
_PROFILE = frozenset({"Patient.telecom.phone", "Patient.birthDate"})


def _visible(patient_id: Id, who: Reader) -> PatientRow:
    """The patient as the reader sees them; another existing one is forbidden, absent not_found."""
    found = container().patient_queries.patients(PatientFilter(ids=(patient_id,)), who).items
    if found:
        return found[0]
    if container().patient_queries.exists(patient_id):
        raise DomainError(ErrorCode.FORBIDDEN, "Cette fiche patient ne vous est pas ouverte.")
    raise missing()


def _response(row: PatientRow) -> HttpResponse:
    return resource_response(to.patient(row), to.version_of(row))


@router.get("/Patient/{resource_id}")
def read_patient(request: HttpRequest, resource_id: str) -> HttpResponse:
    caller(request)
    refuse_undeclared(request.GET, frozenset())
    return _response(_visible(parse_id(resource_id), reader(request)))


def _birth_date(raw: str | None) -> date | None:
    if raw is None:
        return None
    bound = date_bound("birthdate", raw)
    if bound.prefix is not Prefix.EQ or isinstance(bound.value, datetime):
        raise invalid_field("birthdate", "Saisissez une date AAAA-MM-JJ.")
    return bound.value


@router.get("/Patient")
def search_patient(request: HttpRequest) -> HttpResponse:
    caller(request)
    query = search_query(request.GET, PATIENT)
    criteria = PatientFilter(
        name=query.first("name"),
        email=token(query, "email"),
        phone=token(query, "phone"),
        birth_date=_birth_date(query.first("birthdate")),
    )
    page = container().patient_queries.patients(criteria, reader(request), paging_of(query))
    return bundle_response(PATIENT, query, page.total, entries_of(PATIENT, page.items, to.patient))


@router.put("/Patient/{resource_id}")
def update_patient(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    who = reader(request)
    patient_id = parse_id(resource_id)
    _visible(patient_id, who)
    incoming = read_body(request, Patient)
    if incoming.id not in (None, resource_id):
        raise invalid_field("Patient.id", "L'id doit être celui de l'adresse.")
    if identity.user_id != patient_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Seul le patient met à jour sa fiche.")

    def write() -> None:
        changes(
            to.fields(to.patient(_visible(patient_id, who))), to.fields(incoming), writable=_PROFILE
        )
        container().update_profile.execute(user_id=patient_id, **to.profile_values(incoming))

    container().conditional_writes.run(
        target=WriteTarget.user(user_id=patient_id),
        expected=expected_version(request.headers.get("If-Match")),
        current=lambda: to.version_of(_visible(patient_id, who)),
        write=write,
    )
    return _response(_visible(patient_id, who))
