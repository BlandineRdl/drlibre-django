import dataclasses
import uuid

from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.password_hasher import DjangoPasswordHasher
from drlibre.identity.infrastructure.repositories import DjangoSessions, DjangoUsers
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.system_clock import SystemClock

PASSWORD = "correct-horse-1"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.org"


def stored_user(
    role: Role, *, password: str | None = PASSWORD, must_change: bool = False, active: bool = True
) -> User:
    """A user saved through the real repository, with a unique email."""
    at = SystemClock().now()
    user = User(
        id=Id(),
        email=Email(unique_email(role.value.lower())),
        full_name=f"Demo {role.value.title()}",
        role=role,
        active=active,
        password_hash=DjangoPasswordHasher().hash(password) if password else None,
        must_change_password=must_change,
        last_login_at=None,
        created_at=at,
        updated_at=at,
    )
    DjangoUsers().save(user)
    return user


def stored_session(user: User) -> str:
    """Open a session directly, e.g. for a passwordless patient; returns its token."""
    token = uuid.uuid4().hex
    session = Session.after_password(
        token=token, user_id=user.id, role=user.role, user_agent="test", at=SystemClock().now()
    )
    DjangoSessions().add(session)
    return token


def deactivated(user: User) -> User:
    inactive = dataclasses.replace(user, active=False)
    DjangoUsers().save(inactive)
    return inactive
