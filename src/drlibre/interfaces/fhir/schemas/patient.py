from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    ContactPoint,
    DomainResource,
    Extension,
    HumanName,
    Meta,
)


class Patient(DomainResource):
    """Read in full; on update, `id` and `meta` may be left out."""

    resource_type: Literal["Patient"] = "Patient"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    active: bool | None = None
    name: tuple[HumanName, ...] | None = None
    telecom: tuple[ContactPoint, ...] | None = None
    birth_date: str | None = None
