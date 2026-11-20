from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class AppointmentType:
    id: Id
    department_id: Id
    name: str
    code: str
    duration_minutes: int
    buffer_minutes: int
    colour: str
    needs_room: bool
    bookable_online: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_form(
        cls, raw: Raw, *, id: Id, created_at: datetime, at: datetime
    ) -> "AppointmentType":
        f = RecordFields(raw)
        appointment_type = cls(
            id=id,
            department_id=f.reference("department_id", "Choisissez un département."),
            name=f.name(),
            code=f.code(),
            duration_minutes=f.integer("duration_minutes", f.get("duration_minutes"), minimum=1),
            buffer_minutes=f.integer("buffer_minutes", f.get("buffer_minutes"), minimum=0),
            colour=f.colour(),
            needs_room=f.flag("needs_room"),
            bookable_online=f.flag("bookable_online"),
            active=f.flag("active"),
            created_at=created_at,
            updated_at=at,
        )
        f.raise_if_any()
        return appointment_type

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"
