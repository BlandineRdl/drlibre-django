from drlibre.search.application.ports.inbound import SearchHospitals
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.application.use_cases.paging import page_of
from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import HospitalResult, SearchPage
from drlibre.shared_kernel.clock import Clock


class SearchHospitalsUseCase(SearchHospitals):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, criteria: SearchCriteria) -> SearchPage[HospitalResult]:
        horizon = Horizon.at(self._clock.now())
        return page_of(lambda c: self._queries.hospitals(c, horizon), criteria)
