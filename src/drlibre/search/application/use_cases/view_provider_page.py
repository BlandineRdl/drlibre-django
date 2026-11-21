from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.search.application.ports.inbound import ViewProviderPage
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.horizon import Horizon, monday_of
from drlibre.search.domain.results import ProviderWeek
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


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
        zone = ZoneInfo(detail.time_zone)
        today = horizon.now.astimezone(zone).date()
        first, last = monday_of(today), monday_of(horizon.local_days(detail.time_zone)[1])
        monday = monday_of(week) if week is not None else first
        if not first <= monday <= last:
            monday = first
        starts = self._queries.free_starts(
            provider_id,
            kind.id,
            horizon,
            _midnight(monday, zone),
            _midnight(monday + timedelta(days=7), zone),
        )
        return ProviderWeek(
            detail=detail,
            type_id=kind.id,
            monday=monday,
            previous_monday=monday - timedelta(days=7) if monday > first else None,
            next_monday=monday + timedelta(days=7) if monday < last else None,
            starts=starts,
        )


def _midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time(), tzinfo=zone)
