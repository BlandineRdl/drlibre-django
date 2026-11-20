from drlibre.identity.application.ports.inbound import (
    Role,
    StaffLookup,
    StaffMember,
    User,
    UserQueries,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest
from tests.fakes.users import InMemoryUsers


def _member(user: User) -> StaffMember:
    return StaffMember(user.id, user.full_name, user.role, user.active)


class InMemoryUserQueries(UserQueries, StaffLookup):
    """Reads straight from the in-memory users."""

    def __init__(self, users: InMemoryUsers) -> None:
        self.users_store = users

    def _sorted(self) -> list[User]:
        return sorted(self.users_store.rows.values(), key=lambda u: (u.full_name, u.email.value))

    def users(self, request: PageRequest) -> Page[User]:
        needle = request.search.lower()
        found = [
            u for u in self._sorted() if needle in u.full_name.lower() or needle in u.email.value
        ]
        return Page(
            tuple(found[request.offset : request.offset + PAGE_SIZE]), len(found), request.number
        )

    def user(self, user_id: Id) -> User | None:
        return self.users_store.get(user_id)

    def staff_member(self, user_id: Id) -> StaffMember | None:
        user = self.users_store.get(user_id)
        return _member(user) if user else None

    def active_clinicians(self) -> tuple[StaffMember, ...]:
        return tuple(_member(u) for u in self._sorted() if u.role is Role.CLINICIAN and u.active)

    def named_like(self, text: str) -> frozenset[Id]:
        rows = self.users_store.rows.values()
        return frozenset(u.id for u in rows if text.lower() in u.full_name.lower())
