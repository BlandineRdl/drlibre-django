from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class FhirModel(BaseModel):
    """FHIR JSON names are camelCase; unknown elements are refused, not silently dropped."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Coding(FhirModel):
    system: str | None = None
    code: str | None = None
    display: str | None = None


class CodeableConcept(FhirModel):
    coding: tuple[Coding, ...] | None = None
    text: str | None = None


class Reference(FhirModel):
    reference: str | None = None
    display: str | None = None


class Extension(FhirModel):
    url: str
    value_string: str | None = None
    value_boolean: bool | None = None
    value_integer: int | None = None
    value_decimal: float | None = None
    value_code: str | None = None


class Meta(FhirModel):
    version_id: str | None = None
    last_updated: datetime | None = None
