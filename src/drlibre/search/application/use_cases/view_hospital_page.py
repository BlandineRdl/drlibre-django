from drlibre.search.application.ports.inbound import ViewHospitalPage
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.domain.criteria import SearchCriteria, Sort
from drlibre.search.domain.horizon import Horizon
from drlibre.search.domain.results import HospitalPage
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

# Every provider of the hospital on one page.
PROVIDER_LIMIT = 500


class ViewHospitalPageUseCase(ViewHospitalPage):
    def __init__(self, *, clock: Clock, queries: SearchQueries) -> None:
        self._clock = clock
        self._queries = queries

    def execute(self, *, hospital_id: Id) -> HospitalPage:
        detail = self._queries.hospital(hospital_id)
        if detail is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Hôpital introuvable.")
        horizon = Horizon.at(self._clock.now())
        criteria = SearchCriteria(hospital=hospital_id, sort=Sort.NAME_ASC, size=PROVIDER_LIMIT)
        return HospitalPage(
            detail=detail,
            providers=self._queries.providers(criteria, horizon).items,
            first_by_type=self._queries.first_by_type(hospital_id, horizon),
        )
