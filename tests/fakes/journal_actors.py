from drlibre.audit.application.ports.outbound import JournalActors
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.ids import Id
from tests.fakes.users import InMemoryUsers


class InMemoryJournalActors(JournalActors):
    """Reads straight from the in-memory users."""

    def __init__(self, users: InMemoryUsers) -> None:
        self.users = users

    def is_admin(self, user_id: Id) -> bool:
        user = self.users.rows.get(user_id)
        return user is not None and user.active and user.role is Role.ADMIN

    def id_of(self, email: str) -> Id | None:
        wanted = email.strip().lower()
        return next((u.id for u in self.users.rows.values() if u.email.value == wanted), None)

    def emails_of(self, user_ids: frozenset[Id]) -> dict[Id, str]:
        return {i: u.email.value for i in user_ids if (u := self.users.rows.get(i)) is not None}
