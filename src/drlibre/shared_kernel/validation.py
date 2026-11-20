import dataclasses
from typing import Any

from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class FieldErrors:
    """Collects field messages, then raises one invalid_input listing them all."""

    def __init__(self) -> None:
        self._messages: dict[str, str] = {}

    def add(self, field: str, message: str) -> None:
        self._messages.setdefault(field, message)

    def text(self, field: str, raw: str, *, required: bool = True, max_length: int = 200) -> str:
        value = raw.strip()
        if required and not value:
            self.add(field, "Ce champ est obligatoire.")
        elif len(value) > max_length:
            self.add(field, f"{max_length} caractères au plus.")
        return value

    def integer(self, field: str, raw: str, *, minimum: int, default: int | None = None) -> int:
        value = raw.strip()
        if not value and default is not None:
            return default
        try:
            number = int(value)
        except ValueError:
            self.add(field, "Saisissez un nombre entier.")
            return minimum
        if number < minimum:
            self.add(field, f"Saisissez un nombre supérieur ou égal à {minimum}.")
        return number

    def optional_float(self, field: str, raw: str, *, low: float, high: float) -> float | None:
        value = raw.strip().replace(",", ".")
        if not value:
            return None
        try:
            number = float(value)
        except ValueError:
            self.add(field, "Saisissez un nombre.")
            return None
        if not low <= number <= high:
            self.add(field, f"Saisissez une valeur entre {low:g} et {high:g}.")
        return number

    def raise_if_any(self) -> None:
        if self._messages:
            fields = [{"field": name, "message": text} for name, text in self._messages.items()]
            raise DomainError(
                ErrorCode.INVALID_INPUT, "Certains champs sont invalides.", {"fields": fields}
            )


def invalid_field(field: str, message: str) -> DomainError:
    fields = [{"field": field, "message": message}]
    return DomainError(
        ErrorCode.INVALID_INPUT, "Certains champs sont invalides.", {"fields": fields}
    )


def changed_fields(before: Any, after: Any, *, ignore: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Names of the dataclass fields whose value differs between two versions of a record."""
    return tuple(
        field.name
        for field in dataclasses.fields(after)
        if field.name not in ignore and getattr(before, field.name) != getattr(after, field.name)
    )


def parse_id(raw: str) -> Id | None:
    try:
        return Id.parse(raw.strip())
    except ValueError:
        return None
