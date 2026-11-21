from typing import Any, Literal

from drlibre.interfaces.fhir.schemas.common import FhirModel


class BundleLink(FhirModel):
    relation: Literal["self", "next", "previous"]
    url: str


class BundleEntrySearch(FhirModel):
    mode: Literal["match", "include"]


class BundleEntry(FhirModel):
    full_url: str
    resource: dict[str, Any]
    search: BundleEntrySearch


class Bundle(FhirModel):
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset"] = "searchset"
    total: int
    link: tuple[BundleLink, ...]
    entry: tuple[BundleEntry, ...] = ()
