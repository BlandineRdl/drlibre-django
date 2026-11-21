import re
from dataclasses import dataclass
from datetime import date

from drlibre.shared_kernel.validation import FieldErrors

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE = re.compile(r"[0-9+()\-. ]{6,30}")
_OLDEST_BIRTH = date(1900, 1, 1)


@dataclass(frozen=True, slots=True)
class VisitorDetails:
    """What a visitor typed to book; validated, never trusted to identify an existing patient."""

    full_name: str
    birth_date: date
    email: str
    phone: str | None
    reason: str | None

    @classmethod
    def parse(
        cls,
        *,
        full_name: str,
        birth_date: str,
        email: str,
        phone: str,
        reason: str,
        accepted_terms: bool,
        today: date,
    ) -> "VisitorDetails":
        errors = FieldErrors()
        name = errors.text("full_name", full_name, max_length=150)
        born = cls._birth_date(errors, birth_date, today)
        address = email.strip().lower()
        if len(address) > 254 or not _EMAIL.fullmatch(address):
            errors.add("email", "Saisissez une adresse email valide.")
        number = errors.text("phone", phone, required=False, max_length=30)
        if number and not _PHONE.fullmatch(number):
            errors.add("phone", "Saisissez un numéro de téléphone valide.")
        why = errors.text("reason", reason, required=False, max_length=500)
        if not accepted_terms:
            errors.add("accepted_terms", "Acceptez les conditions et la notice de confidentialité.")
        errors.raise_if_any()
        return cls(name, born, address, number or None, why or None)

    @staticmethod
    def _birth_date(errors: FieldErrors, raw: str, today: date) -> date:
        try:
            born = date.fromisoformat(raw.strip())
        except ValueError:
            errors.add("birth_date", "Saisissez une date de naissance valide.")
            return today
        if not _OLDEST_BIRTH <= born <= today:
            errors.add("birth_date", "Saisissez une date de naissance valide.")
        return born

    @property
    def email_domain(self) -> str:
        return self.email.rsplit("@", 1)[1]
