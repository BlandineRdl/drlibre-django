from datetime import datetime
from typing import Literal

from drlibre.interfaces.fhir.schemas.common import (
    CodeableConcept,
    DomainResource,
    FhirModel,
    Meta,
    Reference,
)


class CommunicationPayload(FhirModel):
    content_string: str


class Communication(DomainResource):
    """A notification; its recipient may fill `received` once, nothing else."""

    resource_type: Literal["Communication"] = "Communication"
    id: str | None = None
    meta: Meta | None = None
    status: str
    category: tuple[CodeableConcept, ...] | None = None
    recipient: tuple[Reference, ...] | None = None
    topic: CodeableConcept | None = None
    about: tuple[Reference, ...] | None = None
    payload: tuple[CommunicationPayload, ...] | None = None
    sent: datetime | None = None
    received: datetime | None = None
