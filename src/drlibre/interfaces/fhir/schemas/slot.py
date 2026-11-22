from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    CodeableConcept,
    DomainResource,
    Meta,
    Reference,
)


class Slot(DomainResource):
    resource_type: Literal["Slot"] = "Slot"
    id: str
    meta: Meta
    service_type: tuple[CodeableConcept, ...]
    schedule: Reference
    status: str
    start: str
    end: str
