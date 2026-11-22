from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    CodeableConcept,
    Extension,
    FhirModel,
    Meta,
    Period,
    Reference,
)


class Participant(FhirModel):
    actor: Reference | None = None
    status: str = "accepted"


class Appointment(FhirModel):
    """Read in full; on create, the server fills `id`, `meta`, `end` and the source."""

    resource_type: Literal["Appointment"] = "Appointment"
    id: str | None = None
    meta: Meta | None = None
    extension: tuple[Extension, ...] | None = None
    status: str
    cancelation_reason: CodeableConcept | None = None
    service_type: tuple[CodeableConcept, ...] | None = None
    reason_code: tuple[CodeableConcept, ...] | None = None
    start: str | None = None
    end: str | None = None
    slot: tuple[Reference, ...] | None = None
    comment: str | None = None
    participant: tuple[Participant, ...] | None = None
    requested_period: tuple[Period, ...] | None = None
