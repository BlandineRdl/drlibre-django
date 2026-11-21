from collections.abc import Mapping
from dataclasses import dataclass

from drlibre.shared_kernel.errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"
    required: bool = True
    help: str = ""
    autocomplete: str = "off"


@dataclass(frozen=True, slots=True)
class ChoiceView:
    value: str
    label: str
    selected: bool


@dataclass(frozen=True, slots=True)
class FieldView:
    name: str
    label: str
    kind: str
    required: bool
    help: str
    autocomplete: str
    value: str
    checked: bool
    choices: tuple[ChoiceView, ...]
    error: str
    autofocus: bool
    described_by: str


@dataclass(frozen=True, slots=True)
class ErrorView:
    field: str
    label: str
    message: str


@dataclass(frozen=True, slots=True)
class FormView:
    title: str
    action: str
    submit_label: str
    fields: tuple[FieldView, ...]
    message: str
    errors: tuple[ErrorView, ...]
    cancel_url: str
    cancel_label: str = "Annuler"

    @property
    def has_errors(self) -> bool:
        return bool(self.message)


def field_messages(error: DomainError | None) -> dict[str, str]:
    if error is None or error.code is not ErrorCode.INVALID_INPUT:
        return {}
    return {item["field"]: item["message"] for item in error.details.get("fields", [])}


def build_form(
    *,
    title: str,
    action: str,
    submit_label: str,
    specs: tuple[FieldSpec, ...],
    values: Mapping[str, str],
    error: DomainError | None = None,
    choices: Mapping[str, tuple[Choice, ...]] | None = None,
    cancel_url: str = "",
    cancel_label: str = "Annuler",
) -> FormView:
    """Map raw values and a refusal to the fields the dumb form template renders."""
    messages = field_messages(error)
    first_invalid = next((s.name for s in specs if s.name in messages), None)
    fields = tuple(
        _field(
            spec,
            values,
            messages.get(spec.name, ""),
            (choices or {}).get(spec.name, ()),
            autofocus=spec.name == first_invalid,
        )
        for spec in specs
    )
    labels = {spec.name: spec.label for spec in specs}
    errors = tuple(ErrorView(name, labels.get(name, name), text) for name, text in messages.items())
    return FormView(
        title=title,
        action=action,
        submit_label=submit_label,
        fields=fields,
        message=error.message if error else "",
        errors=errors,
        cancel_url=cancel_url,
        cancel_label=cancel_label,
    )


def _field(
    spec: FieldSpec,
    values: Mapping[str, str],
    error: str,
    choices: tuple[Choice, ...],
    *,
    autofocus: bool,
) -> FieldView:
    raw = "" if spec.kind == "password" else values.get(spec.name, "")
    described = [f"help-{spec.name}"] if spec.help else []
    if error:
        described.append(f"error-{spec.name}")
    return FieldView(
        name=spec.name,
        label=spec.label,
        kind=spec.kind,
        required=spec.required,
        help=spec.help,
        autocomplete=spec.autocomplete,
        value=raw,
        checked=values.get(spec.name) in {"on", "true", "True"},
        choices=tuple(ChoiceView(c.value, c.label, c.value == raw) for c in choices),
        error=error,
        autofocus=autofocus,
        described_by=" ".join(described),
    )
