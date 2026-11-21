from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

from drlibre.interfaces.fhir.params import SearchQuery
from drlibre.interfaces.fhir.schemas.bundle import (
    Bundle,
    BundleEntry,
    BundleEntrySearch,
    BundleLink,
)


def base_url() -> str:
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/fhir"


def entry(
    resource_type: str, resource_id: str, resource: dict[str, Any], *, include: bool = False
) -> BundleEntry:
    return BundleEntry(
        full_url=f"{base_url()}/{resource_type}/{resource_id}",
        resource=resource,
        search=BundleEntrySearch(mode="include" if include else "match"),
    )


def _link(resource_type: str, query: SearchQuery, page: int) -> str:
    pairs = [
        *query.params,
        *(("_sort", s) for s in query.sort),
        *(("_include", i) for i in query.includes),
        ("_count", str(query.count)),
        ("_page", str(page)),
    ]
    return f"{base_url()}/{resource_type}?{urlencode(pairs)}"


def searchset(
    *, resource_type: str, query: SearchQuery, total: int, entries: Sequence[BundleEntry]
) -> Bundle:
    """One page of a search, with absolute self, next and previous links."""
    links = [BundleLink(relation="self", url=_link(resource_type, query, query.page))]
    if query.page * query.count < total:
        links.append(BundleLink(relation="next", url=_link(resource_type, query, query.page + 1)))
    if query.page > 1:
        links.append(
            BundleLink(relation="previous", url=_link(resource_type, query, query.page - 1))
        )
    return Bundle(total=total, link=tuple(links), entry=tuple(entries))
