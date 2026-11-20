from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import SaveUser
from drlibre.identity.application.ports.outbound import (
    PasswordHasher,
    Sessions,
    UpcomingAppointments,
    Users,
)
from drlibre.identity.domain.user import Role, User, UserDetails, check_password_policy
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import changed_fields, invalid_field


class SaveUserUseCase(SaveUser):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        sessions: Sessions,
        hasher: PasswordHasher,
        appointments: UpcomingAppointments,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._appointments = appointments

    def execute(
        self,
        *,
        actor: Id | None,
        user_id: Id | None,
        full_name: str,
        email: str,
        role: str,
        active: bool,
        temporary_password: str,
    ) -> Id:
        at = self._clock.now()
        details = UserDetails.parse(full_name=full_name, email=email, role=role, active=active)
        before = self._existing(user_id) if user_id else None
        holder = self._users.by_email(details.email)
        if holder is not None and (before is None or holder.id != before.id):
            raise invalid_field("email", "Cette adresse est déjà utilisée.")
        if before is None:
            check_password_policy(temporary_password, field="temporary_password")
            after = User.create(
                details=details, password_hash=self._hasher.hash(temporary_password), at=at
            )
        else:
            self._check_edit(actor, before, details)
            after = before.edited(details=details, at=at)
        deactivated = before is not None and before.active and not after.active
        with self._uow:
            self._users.save(after)
            closed = self._sessions.delete_for_user(after.id) if deactivated else 0
            metadata: dict[str, object] = {"role": after.role}
            if before is not None:
                metadata["changed"] = changed_fields(before, after, ignore=("updated_at",))
            if deactivated:
                metadata["sessions_closed"] = closed
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action="user.updated" if before else "user.created",
                    entity_type="user",
                    entity_id=after.id,
                    at=at,
                    metadata=metadata,
                )
            )
        return after.id

    def _existing(self, user_id: Id) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Utilisateur introuvable.")
        return user

    def _check_edit(self, actor: Id | None, before: User, details: UserDetails) -> None:
        if actor == before.id and not details.active:
            raise invalid_field("active", "Vous ne pouvez pas désactiver votre propre compte.")
        if actor == before.id and details.role is not before.role:
            raise invalid_field("role", "Vous ne pouvez pas changer votre propre rôle.")
        if before.active and not details.active and before.role is Role.CLINICIAN:
            upcoming = self._appointments.active_upcoming_for_clinician(
                before.id, after=self._clock.now()
            )
            Dependents(upcoming).refuse_if_any("Ce praticien a des rendez-vous actifs à venir.")
