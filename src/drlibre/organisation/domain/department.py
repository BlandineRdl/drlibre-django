from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Department:
    id: Id
    hospital_id: Id
    name: str
    code: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_form(cls, raw: Raw, *, id: Id, created_at: datetime, at: datetime) -> "Department":
        f = RecordFields(raw)
        department = cls(
            id=id,
            hospital_id=f.reference("hospital_id", "Choisissez un hôpital."),
            name=f.name(),
            code=f.code(),
            description=f.text(
                "description", f.get("description"), required=False, max_length=1000
            ),
            created_at=created_at,
            updated_at=at,
        )
        f.raise_if_any()
        return department

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"
