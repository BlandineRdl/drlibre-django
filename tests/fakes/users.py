from drlibre.identity.application.ports.outbound import Users
from drlibre.identity.domain.user import Email, User
from drlibre.shared_kernel.ids import Id


class InMemoryUsers(Users):
    def __init__(self) -> None:
        self.rows: dict[Id, User] = {}

    def get(self, user_id: Id) -> User | None:
        return self.rows.get(user_id)

    def by_email(self, email: Email) -> User | None:
        return next((u for u in self.rows.values() if u.email == email), None)

    def save(self, user: User) -> None:
        self.rows[user.id] = user

    def delete(self, user_id: Id) -> None:
        self.rows.pop(user_id, None)
