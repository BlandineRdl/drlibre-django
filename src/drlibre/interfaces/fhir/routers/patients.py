from datetime import date, datetime

from django.http import HttpRequest, HttpResponse
from ninja import Router

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity, Role
from drlibre.interfaces.fhir.access import caller, reader, require_admin
from drlibre.interfaces.fhir.bundle import base_url
from drlibre.interfaces.fhir.diff import changes
from drlibre.interfaces.fhir.mappers import directory_writes as writes
from drlibre.interfaces.fhir.mappers import patient as to
from drlibre.interfaces.fhir.outcome import fhir_response
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
from drlibre.interfaces.fhir.version import etag, expected_version
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
        interactions=(
            Interaction.READ,
            Interaction.SEARCH,
            Interaction.CREATE,
            Interaction.UPDATE,
            Interaction.DELETE,
        ),
        search=(
            SearchParam("name", ParamType.STRING),
            SearchParam("email", ParamType.TOKEN),
            SearchParam("phone", ParamType.TOKEN),
            SearchParam("birthdate", ParamType.DATE),
        ),
        sorts=("name",),
    )
)
# The profile screen lets a patient change these two, nothing else; the admin, the others.
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


def _save_user(identity: Identity, user_id: Id | None, incoming: Patient) -> Id:
    """The console's user screen: name, email and active; the patient keeps their profile."""
    values = writes.user_values(incoming)
    return container().save_user.execute(
        actor=identity.user_id,
        user_id=user_id,
        full_name=values.full_name,
        email=values.email,
        role=Role.PATIENT.value,
        active=values.active,
        temporary_password=values.temporary_password,
    )


def _admin_changes(current: Patient, incoming: Patient) -> None:
    changes(
        to.fields(current), to.fields(incoming), writable=writes.PATIENT_WRITABLE, reserved=_PROFILE
    )


@router.post("/Patient")
def create_patient(request: HttpRequest) -> HttpResponse:
    identity = require_admin(request)
    incoming = read_body(request, Patient)
    _admin_changes(Patient(active=True), incoming)
    created = _save_user(identity, None, incoming)
    row = _visible(created, reader(request))
    model = to.patient(row)
    response = fhir_response(model.model_dump_json(by_alias=True, exclude_none=True), status=201)
    response["Location"] = f"{base_url()}/Patient/{created}"
    response["ETag"] = etag(to.version_of(row))
    return response


@router.put("/Patient/{resource_id}")
def update_patient(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = caller(request)
    who = reader(request)
    patient_id = parse_id(resource_id)
    _visible(patient_id, who)
    incoming = read_body(request, Patient)
    if incoming.id not in (None, resource_id):
        raise invalid_field("Patient.id", "L'id doit être celui de l'adresse.")
    if identity.role is not Role.ADMIN and identity.user_id != patient_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Seul le patient met à jour sa fiche.")

    def write() -> None:
        current = to.patient(_visible(patient_id, who))
        if identity.role is Role.ADMIN:
            _admin_changes(current, incoming)
            _save_user(identity, patient_id, incoming)
            return
        changes(to.fields(current), to.fields(incoming), writable=_PROFILE)
        container().update_profile.execute(user_id=patient_id, **to.profile_values(incoming))

    container().conditional_writes.run(
        target=WriteTarget.user(user_id=patient_id),
        expected=expected_version(request.headers.get("If-Match")),
        current=lambda: to.version_of(_visible(patient_id, who)),
        write=write,
    )
    return _response(_visible(patient_id, who))


@router.delete("/Patient/{resource_id}")
def delete_patient(request: HttpRequest, resource_id: str) -> HttpResponse:
    identity = require_admin(request)
    patient_id = parse_id(resource_id)
    _visible(patient_id, reader(request))
    container().delete_user.execute(actor=identity.user_id, user_id=patient_id)
    return HttpResponse(status=204)
