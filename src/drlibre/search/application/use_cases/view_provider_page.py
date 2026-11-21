from datetime import date

from drlibre.search.application.ports.inbound import ViewProviderPage
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import ProviderWeek
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.week import Week


class ViewProviderPageUseCase(ViewProviderPage):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, *, provider_id: Id, type_id: Id | None, week: date | None) -> ProviderWeek:
        detail = self._queries.provider(provider_id)
        if detail is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
        kind = next((t for t in detail.types if t.id == type_id), detail.types[0])
        horizon = Horizon.at(self._clock.now())
        window = Week.within_horizon(asked=week, now=horizon.now, time_zone=detail.time_zone)
        starts = self._queries.free_starts(provider_id, kind.id, horizon, window.start, window.end)
        return ProviderWeek(
            detail=detail,
            type_id=kind.id,
            monday=window.monday,
            previous_monday=window.previous,
            next_monday=window.following,
            starts=starts,
        )
