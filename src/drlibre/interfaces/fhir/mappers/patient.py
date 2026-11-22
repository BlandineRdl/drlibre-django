from drlibre.interfaces.fhir.schemas.common import ContactPoint, HumanName
from drlibre.interfaces.fhir.schemas.patient import Patient
from drlibre.interfaces.fhir.version import meta, version_id
from drlibre.interop.application.ports.inbound import PatientRow


def version_of(row: PatientRow) -> str:
    return version_id(row.updated_at)


def patient(row: PatientRow) -> Patient:
    telecom = (
        ContactPoint(system="email", value=row.email),
        *((ContactPoint(system="phone", value=row.phone),) if row.phone else ()),
    )
    return Patient(
        id=str(row.id),
        meta=meta(version_of(row), row.updated_at),
        active=row.active,
        name=(HumanName(text=row.full_name),),
        telecom=telecom,
        birth_date=row.birth_date.isoformat() if row.birth_date else None,
    )


def _telecom(resource: Patient, system: str) -> tuple[str, ...]:
    return tuple(c.value for c in resource.telecom or () if c.system == system)


def fields(resource: Patient) -> dict[str, object]:
    """The elements an update is compared on, by FHIR path; `id` and `meta` are not among them."""
    return {
        "Patient.active": resource.active,
        "Patient.name": tuple(n.model_dump() for n in resource.name or ()),
        "Patient.telecom.email": _telecom(resource, "email"),
        "Patient.telecom.phone": _telecom(resource, "phone"),
        "Patient.birthDate": resource.birth_date,
    }


def profile_values(resource: Patient) -> dict[str, str]:
    """Phone and birth date as the profile screen sends them, empty when left out."""
    phones = _telecom(resource, "phone")
    return {"phone": phones[0] if phones else "", "birth_date": resource.birth_date or ""}
