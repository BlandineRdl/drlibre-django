from dataclasses import replace

from drlibre.search.application.ports.inbound import ViewSpecialtyPage
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.application.use_cases.paging import page_of
from drlibre.search.domain.criteria import Moment, SearchCriteria, Window
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import SpecialtyPage
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class ViewSpecialtyPageUseCase(ViewSpecialtyPage):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, *, specialty_id: Id, criteria: SearchCriteria) -> SpecialtyPage:
        detail = self._queries.specialty(specialty_id)
        if detail is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Spécialité introuvable.")
        horizon = Horizon.at(self._clock.now())
        own = replace(
            criteria,
            text="",
            specialty=specialty_id,
            hospital=None,
            city="",
            appointment_type=None,
            from_date=None,
            window=Window.ANY,
            moment=Moment.ANY,
        )
        return SpecialtyPage(
            detail=detail, providers=page_of(lambda c: self._queries.providers(c, horizon), own)
        )
