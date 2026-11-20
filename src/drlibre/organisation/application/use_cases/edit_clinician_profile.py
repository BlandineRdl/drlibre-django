from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.organisation.application.ports.inbound import EditClinicianProfile
from drlibre.organisation.application.ports.outbound import (
    ClinicianProfiles,
    Departments,
    Rooms,
    Specialties,
)
from drlibre.organisation.application.use_cases.clinician_profile_rules import check_references
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import changed_fields


class EditClinicianProfileUseCase(EditClinicianProfile):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        profiles: ClinicianProfiles,
        departments: Departments,
        specialties: Specialties,
        rooms: Rooms,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._profiles = profiles
        self._departments = departments
        self._specialties = specialties
        self._rooms = rooms

    def execute(self, *, actor: Id | None, profile_id: Id, fields: Mapping[str, str]) -> None:
        before = self._profiles.get(profile_id)
        if before is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Profil introuvable.")
        at = self._clock.now()
        after = before.edited(fields, at=at)
        check_references(
            after, departments=self._departments, specialties=self._specialties, rooms=self._rooms
        )
        with self._uow:
            self._profiles.save(after)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action="clinician_profile.updated",
                    entity_type="clinician_profile",
                    entity_id=after.id,
                    at=at,
                    metadata={"changed": changed_fields(before, after, ignore=("updated_at",))},
                )
            )
