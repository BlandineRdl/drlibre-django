from zoneinfo import ZoneInfo

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import UpdateProfile
from drlibre.identity.application.ports.outbound import Users
from drlibre.identity.domain.user import ProfileDetails
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import changed_fields


class UpdateProfileUseCase(UpdateProfile):
    def __init__(
        self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, users: Users, time_zone: str
    ) -> None:
        self._clock = clock
        self._zone = ZoneInfo(time_zone)
        self._uow = uow
        self._audit = audit
        self._users = users

    def execute(self, *, actor_id: Id, user_id: Id, phone: str, birth_date: str) -> None:
        # Spec §15.4: only the patient edits these; an admin goes through SaveUser.
        if actor_id != user_id:
            raise DomainError(ErrorCode.FORBIDDEN, "Seul le patient met à jour sa fiche.")
        at = self._clock.now()
        profile = ProfileDetails.parse(
            phone=phone, birth_date=birth_date, today=at.astimezone(self._zone).date()
        )
        with self._uow:
            before = self._users.get(user_id)
            if before is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Compte introuvable.")
            after = before.with_profile(profile=profile, at=at)
            changed = changed_fields(before, after, ignore=("updated_at",))
            if not changed:
                return
            self._users.save(after)
            self._audit.record(
                AuditEntry.from_event(
                    actor=user_id,
                    action="user.profile_updated",
                    entity_type="user",
                    entity_id=user_id,
                    at=at,
                    metadata={"changed": changed},
                )
            )
