import uuid
from contextvars import ContextVar, Token

# The signed-in user of the current request; None for visitors and jobs.
_acting_user: ContextVar[uuid.UUID | None] = ContextVar("acting_user", default=None)


def acting_user_id() -> uuid.UUID | None:
    return _acting_user.get()


def act_as(user_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    """Name the creator of the records inserted until `stop_acting` gets the token back."""
    return _acting_user.set(user_id)


def stop_acting(token: Token[uuid.UUID | None]) -> None:
    _acting_user.reset(token)
