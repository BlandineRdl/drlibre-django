from datetime import date
from typing import Protocol

from drlibre.search.domain.criteria import (
    DEFAULT_PAGE_SIZE as DEFAULT_PAGE_SIZE,
)
from drlibre.search.domain.criteria import (
    PAGE_SIZES as PAGE_SIZES,
)
from drlibre.search.domain.criteria import (
    Location,
    Moment,
    SearchCriteria,
    Sort,
    Window,
)
from drlibre.search.domain.results import (
    BookableType,
    FilterOptions,
    FirstSlot,
    HospitalDetail,
    HospitalPage,
    HospitalResult,
    NextSlots,
    Option,
    ProviderDetail,
    ProviderResult,
    ProviderWeek,
    ResultCounts,
    SearchPage,
    SpecialtyDetail,
    SpecialtyPage,
    SpecialtyResult,
    TypeFirstSlot,
)
from drlibre.shared_kernel.ids import Id

__all__ = [
    "BookableType",
    "CountSearchResults",
    "FilterOptions",
    "FirstSlot",
    "HospitalDetail",
    "HospitalPage",
    "HospitalResult",
    "ListFilterOptions",
    "Location",
    "Moment",
    "NextSlots",
    "Option",
    "ProviderDetail",
    "ProviderResult",
    "ProviderWeek",
    "ResultCounts",
    "SearchCriteria",
    "SearchHospitals",
    "SearchPage",
    "SearchProviders",
    "SearchSpecialties",
    "Sort",
    "SpecialtyDetail",
    "SpecialtyPage",
    "SpecialtyResult",
    "TypeFirstSlot",
    "ViewHospitalPage",
    "ViewProviderPage",
    "ViewSpecialtyPage",
    "Window",
]


class SearchProviders(Protocol):
    def execute(self, criteria: SearchCriteria) -> SearchPage[ProviderResult]:
        """Bookable providers with their next slots; an out-of-range page gives the last."""
        ...


class SearchHospitals(Protocol):
    def execute(self, criteria: SearchCriteria) -> SearchPage[HospitalResult]:
        """Hospitals with a bookable provider and their first slot; the last page when beyond."""
        ...


class SearchSpecialties(Protocol):
    def execute(self, criteria: SearchCriteria) -> SearchPage[SpecialtyResult]:
        """Specialties with a bookable provider and their first slot; the last page when beyond."""
        ...


class CountSearchResults(Protocol):
    def execute(
        self,
        criteria: SearchCriteria,
        *,
        providers: int | None = None,
        hospitals: int | None = None,
        specialties: int | None = None,
    ) -> ResultCounts:
        """Each of the three result list sizes for the same criteria; a size given is kept."""
        ...


class ViewProviderPage(Protocol):
    def execute(self, *, provider_id: Id, type_id: Id | None, week: date | None) -> ProviderWeek:
        """Free starts of the provider's week; not_found if absent, bad type or week default."""
        ...


class ViewHospitalPage(Protocol):
    def execute(self, *, hospital_id: Id) -> HospitalPage:
        """The hospital with its providers' next slots; not_found when absent or inactive."""
        ...


class ViewSpecialtyPage(Protocol):
    def execute(self, *, specialty_id: Id, criteria: SearchCriteria) -> SpecialtyPage:
        """The specialty's providers, paged by the criteria; not_found when absent or inactive."""
        ...


class ListFilterOptions(Protocol):
    def execute(self) -> FilterOptions:
        """The values the filters offer: active specialties, hospitals and online types."""
        ...
