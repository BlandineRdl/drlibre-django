from drlibre.identity.application.ports.outbound import Sessions
from drlibre.identity.domain.session import Session
from drlibre.shared_kernel.ids import Id


class InMemorySessions(Sessions):
    def __init__(self) -> None:
        self.rows: dict[Id, Session] = {}

    def add(self, session: Session) -> None:
        self.rows[session.id] = session

    def by_token_hash(self, token_hash: str) -> Session | None:
        return next((s for s in self.rows.values() if s.token_hash == token_hash), None)

    def save(self, session: Session) -> None:
        self.rows[session.id] = session

    def delete(self, session_id: Id) -> None:
        self.rows.pop(session_id, None)

    def delete_for_user(self, user_id: Id) -> int:
        doomed = [s.id for s in self.rows.values() if s.user_id == user_id]
        for session_id in doomed:
            del self.rows[session_id]
        return len(doomed)
