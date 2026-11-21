from drlibre.booking.application.ports.outbound import Patients
from drlibre.identity.application.ports.inbound import Role, UserQueries
from drlibre.shared_kernel.ids import Id


class IdentityPatients(Patients):
    """Reads patients through identity's UserQueries."""

    def __init__(self, queries: UserQueries) -> None:
        self._queries = queries

    def is_active(self, patient_id: Id) -> bool:
        user = self._queries.user(patient_id)
        return user is not None and user.active and user.role is Role.PATIENT

    def email_domain_of(self, patient_id: Id) -> str | None:
        user = self._queries.user(patient_id)
        return user.email.domain if user is not None and user.role is Role.PATIENT else None

    def email_of(self, patient_id: Id) -> str | None:
        user = self._queries.user(patient_id)
        return user.email.value if user is not None and user.role is Role.PATIENT else None
