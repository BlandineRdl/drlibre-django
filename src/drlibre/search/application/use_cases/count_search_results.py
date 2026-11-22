from collections.abc import Callable
from typing import Any

from drlibre.search.application.ports.inbound import CountSearchResults
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import Found, ResultCounts
from drlibre.shared_kernel.clock import Clock


class CountSearchResultsUseCase(CountSearchResults):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(
        self,
        criteria: SearchCriteria,
        *,
        providers: int | None = None,
        hospitals: int | None = None,
        specialties: int | None = None,
    ) -> ResultCounts:
        horizon = Horizon.at(self._clock.now())
        probe = criteria.on_page(1, 1)

        def size(known: int | None, find: Callable[[SearchCriteria, Horizon], Found[Any]]) -> int:
            return find(probe, horizon).total if known is None else known

        return ResultCounts(
            providers=size(providers, self._queries.providers),
            hospitals=size(hospitals, self._queries.hospitals),
            specialties=size(specialties, self._queries.specialties),
        )
