from collections.abc import Callable
from typing import Protocol

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.scheduling.application.ports.inbound import RefreshSlots
from drlibre.scheduling.application.ports.outbound import Clinician, SchedulingDirectory
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class Owned(Protocol):
    @property
    def clinician_id(self) -> Id: ...


class ClinicianWrites:
    """Steps every clinician's own write shares: caller's profile, ownership, one audited unit."""

    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: SchedulingDirectory,
        refresh: RefreshSlots,
        entity_type: str,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._directory = directory
        self._refresh = refresh
        self._entity_type = entity_type

    def caller(self, actor: Id) -> Clinician:
        clinician = self._directory.clinician_of(actor)
        if clinician is None:
            raise DomainError(ErrorCode.FORBIDDEN, "Réservé aux praticiens ayant un profil.")
        return clinician

    def owned[T: Owned](self, found: T | None, record_id: Id, clinician: Clinician) -> T:
        if found is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.", {"id": str(record_id)})
        if found.clinician_id != clinician.id:
            raise DomainError(ErrorCode.FORBIDDEN, "Cet élément appartient à un autre praticien.")
        return found

    def commit(
        self,
        *,
        actor: Id,
        clinician: Clinician,
        action: str,
        entity_id: Id,
        metadata: dict[str, object],
        write: Callable[[], None],
    ) -> None:
        """Write, audit and refresh the clinician's slots in one unit of work."""
        with self._uow:
            write()
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action=f"{self._entity_type}.{action}",
                    entity_type=self._entity_type,
                    entity_id=entity_id,
                    at=self._clock.now(),
                    metadata=metadata,
                )
            )
            self._refresh.execute(clinician_id=clinician.id)
