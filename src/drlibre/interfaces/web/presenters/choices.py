from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ChoiceView:
    value: str
    label: str
    selected: bool
