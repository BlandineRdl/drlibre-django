from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Room:
    id: Id
    department_id: Id
    name: str
    code: str
    floor: str
    capacity: int
    equipment: tuple[str, ...]
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_form(cls, raw: Raw, *, id: Id, created_at: datetime, at: datetime) -> "Room":
        f = RecordFields(raw)
        equipment = tuple(item.strip() for item in f.get("equipment").split(",") if item.strip())
        room = cls(
            id=id,
            department_id=f.reference("department_id", "Choisissez un département."),
            name=f.name(),
            code=f.code(),
            floor=f.text("floor", f.get("floor"), max_length=20),
            capacity=f.integer("capacity", f.get("capacity"), minimum=1),
            equipment=equipment,
            active=f.flag("active"),
            created_at=created_at,
            updated_at=at,
        )
        f.raise_if_any()
        return room

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"
