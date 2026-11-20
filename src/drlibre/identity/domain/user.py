import dataclasses
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors, invalid_field

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 72
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class Role(StrEnum):
    ADMIN = "ADMIN"
    CLINICIAN = "CLINICIAN"
    PATIENT = "PATIENT"


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    @classmethod
    def parse(cls, raw: str, *, field: str = "email") -> "Email":
        value = raw.strip().lower()
        if len(value) > 254 or not _EMAIL.fullmatch(value):
            raise invalid_field(field, "Saisissez une adresse email valide.")
        return cls(value)

    @property
    def domain(self) -> str:
        return self.value.rsplit("@", 1)[1]


def check_password_policy(raw: str, *, field: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(raw) <= PASSWORD_MAX_LENGTH:
        message = f"De {PASSWORD_MIN_LENGTH} à {PASSWORD_MAX_LENGTH} caractères."
        raise invalid_field(field, message)


@dataclass(frozen=True, slots=True)
class UserDetails:
    """Validated fields an admin sets on an account."""

    full_name: str
    email: Email
    role: Role
    active: bool

    @classmethod
    def parse(cls, *, full_name: str, email: str, role: str, active: bool) -> "UserDetails":
        errors = FieldErrors()
        name = errors.text("full_name", full_name, max_length=150)
        try:
            parsed_email = Email.parse(email)
        except DomainError:
            errors.add("email", "Saisissez une adresse email valide.")
            parsed_email = Email("")
        parsed_role = Role.__members__.get(role.strip().upper())
        if parsed_role is None:
            errors.add("role", "Choisissez un rôle.")
            parsed_role = Role.PATIENT
        errors.raise_if_any()
        return cls(name, parsed_email, parsed_role, active)


@dataclass(frozen=True, slots=True)
class User:
    id: Id
    email: Email
    full_name: str
    role: Role
    active: bool
    password_hash: str | None
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, details: UserDetails, password_hash: str, at: datetime) -> "User":
        return cls(
            id=Id(),
            email=details.email,
            full_name=details.full_name,
            role=details.role,
            active=details.active,
            password_hash=password_hash,
            must_change_password=True,
            last_login_at=None,
            created_at=at,
            updated_at=at,
        )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    def edited(self, *, details: UserDetails, at: datetime) -> "User":
        return dataclasses.replace(
            self,
            email=details.email,
            full_name=details.full_name,
            role=details.role,
            active=details.active,
            updated_at=at,
        )

    def with_password(self, *, password_hash: str, at: datetime) -> "User":
        return dataclasses.replace(
            self, password_hash=password_hash, must_change_password=False, updated_at=at
        )

    def signed_in(self, *, at: datetime) -> "User":
        return dataclasses.replace(self, last_login_at=at)
