from datetime import datetime
from typing import Protocol

from drlibre.search.domain.criteria import SearchCriteria
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import (
    FilterOptions,
    Found,
    HospitalDetail,
    HospitalResult,
    ProviderDetail,
    ProviderResult,
    SpecialtyDetail,
    SpecialtyResult,
    TypeFirstSlot,
)
from drlibre.shared_kernel.ids import Id


class SearchQueries(Protocol):
    def providers(self, criteria: SearchCriteria, horizon: Horizon) -> Found[ProviderResult]:
        """The criteria's page of bookable providers, ordered over the whole set; may be empty."""
        ...

    def hospitals(self, criteria: SearchCriteria, horizon: Horizon) -> Found[HospitalResult]:
        """The criteria's page of hospitals with a bookable provider, ordered over the whole set."""
        ...

    def specialties(self, criteria: SearchCriteria, horizon: Horizon) -> Found[SpecialtyResult]:
        """The criteria's page of specialties with a bookable provider, over the whole set."""
        ...

    def provider(self, provider_id: Id) -> ProviderDetail | None:
        """Public details of a bookable provider, None when absent, inactive or not bookable."""
        ...

    def hospital(self, hospital_id: Id) -> HospitalDetail | None:
        """Public details of an active hospital, None when absent or inactive."""
        ...

    def specialty(self, specialty_id: Id) -> SpecialtyDetail | None:
        """Public details of an active specialty, None when absent or inactive."""
        ...

    def free_starts(
        self, provider_id: Id, type_id: Id, horizon: Horizon, start: datetime, end: datetime
    ) -> tuple[datetime, ...]:
        """Free, unheld starts of the type within the horizon and [start, end), earliest first."""
        ...

    def first_by_type(self, hospital_id: Id, horizon: Horizon) -> tuple[TypeFirstSlot, ...]:
        """Each active online type of the hospital with its first free start, None when none."""
        ...

    def filter_options(self) -> FilterOptions:
        """Active specialties, active hospitals and active online types, each by label."""
        ...
