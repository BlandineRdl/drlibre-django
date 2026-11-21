from drlibre.search.application.ports.inbound import SearchSpecialties
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.application.use_cases.paging import page_of
from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import SearchPage, SpecialtyResult
from drlibre.shared_kernel.clock import Clock


class SearchSpecialtiesUseCase(SearchSpecialties):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, criteria: SearchCriteria) -> SearchPage[SpecialtyResult]:
        horizon = Horizon.at(self._clock.now())
        return page_of(lambda c: self._queries.specialties(c, horizon), criteria)
