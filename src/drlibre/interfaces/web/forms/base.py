from collections.abc import Iterable
from datetime import date
from typing import Any, cast

from django import forms

from drlibre.shared_kernel.errors import DomainError, ErrorCode

CHOOSE = ("", "Choisir…")
INVALID = ErrorCode.INVALID_INPUT.http_status


def options(items: Iterable[Any]) -> tuple[tuple[str, str], ...]:
    """Picklist choices of read-side options, each with an `id` and a `label`."""
    return tuple((str(o.id), o.label) for o in items)


def with_placeholder(choices: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    return [CHOOSE, *choices]


class TelInput(forms.TextInput):
    input_type = "tel"


def iso(day: date | None) -> str:
    """A cleaned optional date as the ISO text use cases parse."""
    return day.isoformat() if day else ""


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
        if not self.is_bound:
            # Lets an untouched form still carry a refusal through add_error.
            self.cleaned_data = {}
        self._focus_first_error()

    def refuse(self, error: DomainError, message: str = "") -> None:
        """Attach a use case refusal to its fields, else `message` or its own to the form."""
        fields = error.details.get("fields", []) if error.code is ErrorCode.INVALID_INPUT else []
        named = [item for item in fields if item["field"] in self.fields]
        for item in named:
            self.add_error(item["field"], item["message"])
        if not named:
            self.add_error(None, message or error.message)
        self._focus_first_error()

    @property
    def errored_fields(self) -> list[forms.BoundField]:
        """Visible fields with an error, as the error summary links them."""
        return [field for field in self.visible_fields() if field.errors]

    def posted(self) -> dict[str, str]:
        """The posted text of this form's fields, as use cases taking raw fields parse it."""
        return {name: self.data.get(name, "") for name in self.fields}

    def offer(self, name: str, choices: Iterable[tuple[str, str]]) -> None:
        """Set a select's choices known only at request time, after « Choisir… »."""
        field = cast("forms.ChoiceField", self.fields[name])
        field.choices = with_placeholder(choices)

    def _focus_first_error(self) -> None:
        first = next((name for name in self.fields if name in self.errors), None)
        for name, field in self.fields.items():
            if name == first:
                field.widget.attrs["autofocus"] = True
            else:
                field.widget.attrs.pop("autofocus", None)
