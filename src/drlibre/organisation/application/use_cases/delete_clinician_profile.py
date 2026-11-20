from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.organisation.application.ports.inbound import DeleteClinicianProfile
from drlibre.organisation.application.ports.outbound import ClinicianProfiles, ScheduleDependents
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteClinicianProfileUseCase(DeleteClinicianProfile):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        profiles: ClinicianProfiles,
        schedule: ScheduleDependents,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._profiles = profiles
        self._schedule = schedule

    def execute(self, *, actor: Id | None, profile_id: Id) -> None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Profil introuvable.")
        with self._uow:
            # Checked inside the unit, so the refusal and the delete see the same rows.
            Dependents(self._schedule.for_clinician_profile(profile.id)).refuse_if_any(
                "Ce praticien a des rendez-vous."
            )
            self._profiles.delete(profile.id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action="clinician_profile.deleted",
                    entity_type="clinician_profile",
                    entity_id=profile.id,
                    at=self._clock.now(),
                    metadata={"user": profile.user_id},
                )
            )
