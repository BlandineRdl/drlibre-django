from datetime import datetime
from typing import Protocol

from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import Email, User
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class Users(Protocol):
    def get(self, user_id: Id) -> User | None:
        """Return the user, or None when absent."""
        ...

    def by_email(self, email: Email) -> User | None:
        """Return the user holding this lower-case email, or None."""
        ...

    def save(self, user: User) -> None:
        """Insert or replace the user by id."""
        ...

    def delete(self, user_id: Id) -> None:
        """Remove the user and their sessions; callers check what still uses it first."""
        ...


class Sessions(Protocol):
    def add(self, session: Session) -> None:
        """Store a new session."""
        ...

    def by_token_hash(self, token_hash: str) -> Session | None:
        """Return the session with this token hash, or None."""
        ...

    def save(self, session: Session) -> None:
        """Replace a stored session by id."""
        ...

    def delete(self, session_id: Id) -> None:
        """Remove the session; absent is a no-op."""
        ...

    def delete_for_user(self, user_id: Id) -> int:
        """Remove every session of the user and return how many there were."""
        ...


class PasswordHasher(Protocol):
    def hash(self, raw: str) -> str:
        """Return a slow salted hash of the password."""
        ...

    def verify(self, raw: str, hashed: str | None) -> bool:
        """Check the password; with no hash, spend the same time and return False."""
        ...


class FailedSignIns(Protocol):
    def record(self, email: Email, *, at: datetime) -> None:
        """Count one failed sign-in for this address at this instant."""
        ...

    def count_since(self, email: Email, *, since: datetime) -> int:
        """Return how many failures this address has had since the instant."""
        ...

    def clear(self, email: Email) -> None:
        """Forget every failure of this address."""
        ...


class TokenGenerator(Protocol):
    def new_token(self) -> str:
        """Return an unguessable random token."""
        ...


class UpcomingAppointments(Protocol):
    def active_upcoming_for_clinician(
        self, clinician_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        """Active appointments of the clinician starting after the instant."""
        ...

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        """Every appointment where the user is the patient or the clinician."""
        ...


class AuditActors(Protocol):
    def has_acted(self, user_id: Id) -> bool:
        """True when the user is the actor of at least one audit entry."""
        ...


class StaffProfiles(Protocol):
    def profile_of(self, user_id: Id) -> Dependent | None:
        """The clinician profile attached to the user, as a dependent, or None."""
        ...
