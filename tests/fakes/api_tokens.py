from drlibre.identity.application.ports.outbound import ApiTokens
from drlibre.identity.domain.api_token import ApiToken
from drlibre.shared_kernel.ids import Id


class InMemoryApiTokens(ApiTokens):
    def __init__(self) -> None:
        self.rows: dict[Id, ApiToken] = {}

    def add(self, token: ApiToken) -> None:
        self.rows[token.id] = token

    def by_token_hash(self, token_hash: str) -> ApiToken | None:
        return next((t for t in self.rows.values() if t.token_hash == token_hash), None)

    def delete_for_user(self, user_id: Id) -> int:
        doomed = [t.id for t in self.rows.values() if t.user_id == user_id]
        for token_id in doomed:
            del self.rows[token_id]
        return len(doomed)
