from drlibre.booking.application.ports.inbound import RequirePatient
from drlibre.booking.application.ports.outbound import Patients
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

PATIENTS_ONLY = "Réservé aux patients actifs."


def refuse_non_patient(patients: Patients, user_id: Id) -> None:
    if not patients.is_active(user_id):
        raise DomainError(ErrorCode.FORBIDDEN, PATIENTS_ONLY)


class RequirePatientUseCase(RequirePatient):
    def __init__(self, *, patients: Patients) -> None:
        self._patients = patients

    def execute(self, *, user_id: Id) -> None:
        refuse_non_patient(self._patients, user_id)
