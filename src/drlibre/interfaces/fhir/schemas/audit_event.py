from datetime import datetime
from typing import Literal

from drlibre.interfaces.fhir.schemas.common import Coding, Extension, FhirModel, Meta, Reference


class AuditEventAgent(FhirModel):
    who: Reference | None = None
    name: str | None = None
    requestor: bool


class AuditEventSource(FhirModel):
    observer: Reference


class AuditEventDetail(FhirModel):
    type: str
    value_string: str


class AuditEventEntity(FhirModel):
    what: Reference | None = None
    type: Coding | None = None
    detail: tuple[AuditEventDetail, ...] | None = None


class AuditEvent(FhirModel):
    """An audit entry, read only; the correlation id rides in an extension."""

    resource_type: Literal["AuditEvent"] = "AuditEvent"
    id: str
    meta: Meta
    extension: tuple[Extension, ...] | None = None
    type: Coding
    subtype: tuple[Coding, ...]
    action: str
    recorded: datetime
    agent: tuple[AuditEventAgent, ...]
    source: AuditEventSource
    entity: tuple[AuditEventEntity, ...] | None = None
