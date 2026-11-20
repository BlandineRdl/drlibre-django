from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import ChangePassword
from drlibre.identity.application.ports.outbound import PasswordHasher, Users
from drlibre.identity.domain.user import check_password_policy
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class ChangePasswordUseCase(ChangePassword):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        hasher: PasswordHasher,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._hasher = hasher

    def execute(self, *, user_id: Id, current_password: str, new_password: str) -> None:
        user = self._users.get(user_id)
        if user is None or user.password_hash is None:
            raise DomainError(ErrorCode.FORBIDDEN, "Ce compte n'a pas de mot de passe.")
        if not self._hasher.verify(current_password, user.password_hash):
            raise invalid_field("current_password", "Le mot de passe actuel est incorrect.")
        if new_password == current_password:
            raise invalid_field("new_password", "Choisissez un mot de passe différent de l'actuel.")
        check_password_policy(new_password, field="new_password")
        at = self._clock.now()
        with self._uow:
            self._users.save(
                user.with_password(password_hash=self._hasher.hash(new_password), at=at)
            )
            self._audit.record(
                AuditEntry.from_event(
                    actor=user.id,
                    action="user.password_changed",
                    entity_type="user",
                    entity_id=user.id,
                    at=at,
                )
            )
