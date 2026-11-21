from collections.abc import Callable

from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.results import Found, SearchPage


def page_of[T](
    find: Callable[[SearchCriteria], Found[T]], criteria: SearchCriteria
) -> SearchPage[T]:
    """Run the query; when the page is past the end, answer the last one."""
    found = find(criteria)
    pages = max(1, -(-found.total // criteria.size))
    if not found.items and criteria.page > 1:
        total = find(criteria.on_page(1)).total
        pages = max(1, -(-total // criteria.size))
        found = find(criteria.on_page(pages))
        return SearchPage(found.items, found.total, pages, pages, criteria.size)
    return SearchPage(found.items, found.total, criteria.page, pages, criteria.size)
