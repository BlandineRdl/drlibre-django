from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Specialty:
    id: Id
    name: str
    code: str
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_form(cls, raw: Raw, *, id: Id, created_at: datetime, at: datetime) -> "Specialty":
        f = RecordFields(raw)
        specialty = cls(id, f.name(), f.code(), f.flag("active"), created_at, at)
        f.raise_if_any()
        return specialty

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"
