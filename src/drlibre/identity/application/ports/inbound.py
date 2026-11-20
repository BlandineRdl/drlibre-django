from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from drlibre.identity.domain.user import Role, User
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

__all__ = [
    "AuthenticateSession",
    "ChangePassword",
    "DeleteUser",
    "Identity",
    "Role",
    "SaveUser",
    "SignIn",
    "SignOut",
    "SignedIn",
    "StaffLookup",
    "StaffMember",
    "User",
    "UserQueries",
]


@dataclass(frozen=True, slots=True)
class Identity:
    user_id: Id
    role: Role
    full_name: str
    has_password: bool
    must_change_password: bool
    session_expires_at: datetime
    session_renewed: bool


@dataclass(frozen=True, slots=True)
class SignedIn:
    token: str
    role: Role
    expires_at: datetime


class SignIn(Protocol):
    def execute(self, *, email: str, password: str, user_agent: str) -> SignedIn:
        """Open a session; raise unauthenticated with one message for every refusal."""
        ...


class SignOut(Protocol):
    def execute(self, *, token: str) -> None:
        """Delete the session of this token; an unknown token is a no-op."""
        ...


class AuthenticateSession(Protocol):
    def execute(self, *, token: str) -> Identity | None:
        """Return who holds this token, extending the session; None if expired or inactive."""
        ...


class ChangePassword(Protocol):
    def execute(self, *, user_id: Id, current_password: str, new_password: str) -> None:
        """Replace the password; raise forbidden without one, invalid_input on a bad field."""
        ...


@dataclass(frozen=True, slots=True)
class StaffMember:
    user_id: Id
    full_name: str
    role: Role
    active: bool


class SaveUser(Protocol):
    def execute(
        self,
        *,
        actor: Id | None,
        user_id: Id | None,
        full_name: str,
        email: str,
        role: str,
        active: bool,
        temporary_password: str,
    ) -> Id:
        """Create (with a temporary password) or edit an account; invalid_input, has_dependents."""
        ...


class DeleteUser(Protocol):
    def execute(self, *, actor: Id | None, user_id: Id) -> None:
        """Delete an account; forbidden for one's own, has_dependents when it is still used."""
        ...


class UserQueries(Protocol):
    def users(self, request: PageRequest) -> Page[User]:
        """Users matching the search on name or email, 20 per page, by name."""
        ...

    def user(self, user_id: Id) -> User | None:
        """One user, active or not, or None."""
        ...


class StaffLookup(Protocol):
    def staff_member(self, user_id: Id) -> StaffMember | None:
        """The user as staff, active or not, or None."""
        ...

    def active_clinicians(self) -> tuple[StaffMember, ...]:
        """Every active clinician user, by name."""
        ...

    def named_like(self, text: str) -> frozenset[Id]:
        """Users whose full name contains the text, ignoring case."""
        ...
