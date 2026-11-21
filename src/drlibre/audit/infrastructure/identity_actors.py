from drlibre.audit.application.ports.outbound import JournalActors
from drlibre.identity.application.ports.inbound import Role, StaffLookup, UserQueries
from drlibre.shared_kernel.ids import Id


class IdentityJournalActors(JournalActors):
    """Reads users and admin roles through identity's queries."""

    def __init__(self, *, users: UserQueries, staff: StaffLookup) -> None:
        self._users = users
        self._staff = staff

    def is_admin(self, user_id: Id) -> bool:
        member = self._staff.staff_member(user_id)
        return member is not None and member.active and member.role is Role.ADMIN

    def id_of(self, email: str) -> Id | None:
        user = self._users.user_by_email(email)
        return user.id if user else None

    def emails_of(self, user_ids: frozenset[Id]) -> dict[Id, str]:
        return {i: u.email.value for i in user_ids if (u := self._users.user(i)) is not None}
