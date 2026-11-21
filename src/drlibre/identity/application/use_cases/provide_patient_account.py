from datetime import date

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import ProvidePatientAccount
from drlibre.identity.application.ports.outbound import Users
from drlibre.identity.domain.user import Email, PatientDetails, Role, User
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork

REFUSED = "Cette réservation ne peut pas être effectuée."


class ProvidePatientAccountUseCase(ProvidePatientAccount):
    def __init__(self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, users: Users) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users

    def execute(self, *, full_name: str, email: str, birth_date: date, phone: str | None) -> Id:
        address = Email.parse(email)
        existing = self._users.by_email(address)
        if existing is not None:
            if existing.role is not Role.PATIENT or not existing.active:
                raise DomainError(ErrorCode.FORBIDDEN, REFUSED)
            return existing.id
        at = self._clock.now()
        patient = User.passwordless_patient(
            details=PatientDetails(full_name, address, birth_date, phone), at=at
        )
        with self._uow:
            self._users.save(patient)
            self._audit.record(
                AuditEntry.from_event(
                    actor=patient.id,
                    action="identity.patient_created",
                    entity_type="user",
                    entity_id=patient.id,
                    at=at,
                    metadata={"email_domain": address.domain},
                )
            )
        return patient.id
