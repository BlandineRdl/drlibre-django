from drlibre.identity.application.ports.outbound import StaffProfiles
from drlibre.organisation.application.ports.inbound import ReferenceQueries
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class OrganisationStaffProfiles(StaffProfiles):
    """Asks the organisation context, through its inbound port, for the user's clinician profile."""

    def __init__(self, queries: ReferenceQueries) -> None:
        self._queries = queries

    def profile_of(self, user_id: Id) -> Dependent | None:
        profile = self._queries.clinician_profile_of(user_id)
        return Dependent("clinician", profile.id, profile.title) if profile else None
