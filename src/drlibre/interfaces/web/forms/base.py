from collections.abc import Iterable
from typing import Any

from django import forms

from drlibre.shared_kernel.errors import DomainError, ErrorCode

CHOOSE = ("", "Choisir…")


def with_placeholder(choices: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    return [CHOOSE, *choices]


class WebForm(forms.Form):
    """Input shape of one screen, rendered with the error summary and first-error focus."""

    template_name = "forms/form.html"
    invalid_message = "Certains champs sont invalides."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "field-%s")
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def full_clean(self) -> None:
        super().full_clean()
        self._focus_first_error()

    def refuse(self, error: DomainError) -> None:
        """Attach a use case refusal to its fields, or to the form when no field names it."""
        fields = error.details.get("fields", []) if error.code is ErrorCode.INVALID_INPUT else []
        named = [item for item in fields if item["field"] in self.fields]
        for item in named:
            self.add_error(item["field"], item["message"])
        if not named:
            self.add_error(None, error.message)
        self._focus_first_error()

    def _focus_first_error(self) -> None:
        first = next((name for name in self.fields if name in self.errors), None)
        for name, field in self.fields.items():
            if name == first:
                field.widget.attrs["autofocus"] = True
            else:
                field.widget.attrs.pop("autofocus", None)
