from drlibre.search.application.ports.inbound import ListFilterOptions
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.results import FilterOptions


class ListFilterOptionsUseCase(ListFilterOptions):
    def __init__(self, *, queries: SearchQueries) -> None:
        self._queries = queries

    def execute(self) -> FilterOptions:
        return self._queries.filter_options()
