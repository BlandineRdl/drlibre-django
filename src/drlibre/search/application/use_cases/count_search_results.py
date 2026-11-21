from drlibre.search.application.ports.inbound import CountSearchResults
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import ResultCounts
from drlibre.shared_kernel.clock import Clock


class CountSearchResultsUseCase(CountSearchResults):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, criteria: SearchCriteria) -> ResultCounts:
        horizon = Horizon.at(self._clock.now())
        probe = criteria.on_page(1, 1)
        return ResultCounts(
            providers=self._queries.providers(probe, horizon).total,
            hospitals=self._queries.hospitals(probe, horizon).total,
            specialties=self._queries.specialties(probe, horizon).total,
        )
