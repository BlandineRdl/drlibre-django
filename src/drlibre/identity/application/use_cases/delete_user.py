from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import DeleteUser
from drlibre.identity.application.ports.outbound import (
    AuditActors,
    Sessions,
    StaffProfiles,
    UpcomingAppointments,
    Users,
)
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependent, Dependents
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork

DEACTIVATE_INSTEAD = "Désactivez ce compte plutôt que de le supprimer."


class DeleteUserUseCase(DeleteUser):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        sessions: Sessions,
        appointments: UpcomingAppointments,
        actors: AuditActors,
        profiles: StaffProfiles,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._appointments = appointments
        self._actors = actors
        self._profiles = profiles

    def execute(self, *, actor: Id | None, user_id: Id) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Utilisateur introuvable.")
        if actor == user.id:
            raise DomainError(
                ErrorCode.FORBIDDEN,
                f"Vous ne pouvez pas supprimer votre compte. {DEACTIVATE_INSTEAD}",
            )
        with self._uow:
            # Checked inside the unit, so the refusal and the delete see the same rows.
            self._dependents(user.id).refuse_if_any(
                f"Ce compte est encore référencé. {DEACTIVATE_INSTEAD}"
            )
            self._sessions.delete_for_user(user.id)
            self._users.delete(user.id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action="user.deleted",
                    entity_type="user",
                    entity_id=user.id,
                    at=self._clock.now(),
                    metadata={"role": user.role},
                )
            )

    def _dependents(self, user_id: Id) -> Dependents:
        audited = (
            (Dependent("audit_entry", user_id, "Entrées du journal d'audit"),)
            if self._actors.has_acted(user_id)
            else ()
        )
        profile = self._profiles.profile_of(user_id)
        return Dependents.of(
            self._appointments.any_for_user(user_id), audited, (profile,) if profile else ()
        )
