from typing import Literal

from drlibre.interfaces.fhir.schemas.common import FhirModel, Meta, Reference


class AppointmentResponse(FhirModel):
    """An accepted offer; on create the server fills `id`, `meta` and the actor, its patient."""

    resource_type: Literal["AppointmentResponse"] = "AppointmentResponse"
    id: str | None = None
    meta: Meta | None = None
    appointment: Reference
    actor: Reference | None = None
    participant_status: str
