from typing import Literal

from drlibre.interfaces.fhir.schemas.common import ContactPoint, FhirModel, HumanName, Meta


class Patient(FhirModel):
    """Read in full; on update, `id` and `meta` may be left out."""

    resource_type: Literal["Patient"] = "Patient"
    id: str | None = None
    meta: Meta | None = None
    active: bool | None = None
    name: tuple[HumanName, ...] | None = None
    telecom: tuple[ContactPoint, ...] | None = None
    birth_date: str | None = None
