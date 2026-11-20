from drlibre.identity.application.ports.inbound import AuthenticateSession, Identity
from drlibre.identity.application.ports.outbound import Sessions, Users
from drlibre.identity.domain.session import hash_token
from drlibre.shared_kernel.clock import Clock


class AuthenticateSessionUseCase(AuthenticateSession):
    def __init__(self, *, clock: Clock, users: Users, sessions: Sessions) -> None:
        self._clock = clock
        self._users = users
        self._sessions = sessions

    def execute(self, *, token: str) -> Identity | None:
        at = self._clock.now()
        session = self._sessions.by_token_hash(hash_token(token))
        if session is None or session.is_expired(at=at):
            return None
        user = self._users.get(session.user_id)
        if user is None or not user.active:
            return None
        renewed = session.needs_extension(at=at)
        if renewed:
            session = session.extended(at=at)
            # Extending the expiry is session upkeep, not a business change, so it is not audited.
            self._sessions.save(session)
        return Identity(
            user_id=user.id,
            role=user.role,
            full_name=user.full_name,
            has_password=user.has_password,
            must_change_password=user.must_change_password,
            session_expires_at=session.expires_at,
            session_renewed=renewed,
        )
