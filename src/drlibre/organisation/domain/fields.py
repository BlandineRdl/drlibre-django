import re
from collections.abc import Mapping
from functools import cache
from zoneinfo import available_timezones

from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors, parse_id

_CODE = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,29}")
_COLOUR = re.compile(r"#[0-9A-Fa-f]{6}")

type Raw = Mapping[str, str]


@cache
def _time_zones() -> frozenset[str]:
    return frozenset(available_timezones())


class RecordFields(FieldErrors):
    """Field parsers shared by the referential records, reading raw form text."""

    def __init__(self, raw: Raw) -> None:
        super().__init__()
        self.raw = raw

    def get(self, name: str) -> str:
        return self.raw.get(name, "")

    def name(self) -> str:
        return self.text("name", self.get("name"), max_length=150)

    def code(self) -> str:
        value = self.get("code").strip().upper()
        if not _CODE.fullmatch(value):
            self.add("code", "1 à 30 lettres, chiffres, tirets ou soulignés.")
        return value

    def flag(self, name: str) -> bool:
        return self.get(name) in {"on", "true", "True", "1"}

    def reference(self, name: str, message: str) -> Id:
        parsed = parse_id(self.get(name))
        if parsed is None:
            self.add(name, message)
            return Id()
        return parsed

    def time_zone(self) -> str:
        value = self.get("time_zone").strip()
        if value not in _time_zones():
            self.add("time_zone", "Choisissez un fuseau horaire IANA, par exemple Europe/Paris.")
        return value

    def colour(self) -> str:
        value = self.get("colour").strip()
        if not _COLOUR.fullmatch(value):
            self.add("colour", "Saisissez une couleur au format #RRGGBB.")
        return value.upper()
