import dataclasses
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors, invalid_field

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 72
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE = re.compile(r"[0-9 +()\-]{7,20}")


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
class ProfileDetails:
    """Phone and birth date a user edits on their profile; None clears the value."""

    phone: str | None
    birth_date: date | None

    @classmethod
    def parse(cls, *, phone: str, birth_date: str, today: date) -> "ProfileDetails":
        errors = FieldErrors()
        phone_value = phone.strip() or None
        if phone_value is not None and not _PHONE.fullmatch(phone_value):
            errors.add("phone", "De 7 à 20 caractères parmi chiffres, espaces et + ( ) -.")
        birth_value = None
        if raw_birth := birth_date.strip():
            try:
                birth_value = date.fromisoformat(raw_birth)
            except ValueError:
                errors.add("birth_date", "Saisissez une date réelle.")
            else:
                if birth_value > today:
                    errors.add("birth_date", "La date de naissance ne peut pas être future.")
        errors.raise_if_any()
        return cls(phone_value, birth_value)


@dataclass(frozen=True, slots=True)
class PatientDetails:
    """Validated profile of a patient created from a booking."""

    full_name: str
    email: Email
    birth_date: date
    phone: str | None


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
    phone: str | None = None
    birth_date: date | None = None
    email_verified_at: datetime | None = None

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

    @classmethod
    def passwordless_patient(cls, *, details: "PatientDetails", at: datetime) -> "User":
        """A patient with no password, whose email was proven by a code."""
        return cls(
            id=Id(),
            email=details.email,
            full_name=details.full_name,
            role=Role.PATIENT,
            active=True,
            password_hash=None,
            must_change_password=False,
            last_login_at=None,
            created_at=at,
            updated_at=at,
            phone=details.phone,
            birth_date=details.birth_date,
            email_verified_at=at,
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

    def with_profile(self, *, profile: ProfileDetails, at: datetime) -> "User":
        return dataclasses.replace(
            self, phone=profile.phone, birth_date=profile.birth_date, updated_at=at
        )

    def with_password(self, *, password_hash: str, at: datetime) -> "User":
        return dataclasses.replace(
            self, password_hash=password_hash, must_change_password=False, updated_at=at
        )

    def signed_in(self, *, at: datetime) -> "User":
        return dataclasses.replace(self, last_login_at=at)
