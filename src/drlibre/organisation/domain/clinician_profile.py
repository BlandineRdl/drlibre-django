from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import parse_id

DEFAULT_WEIGHT = 1


@dataclass(frozen=True, slots=True)
class ClinicianProfile:
    id: Id
    user_id: Id
    department_id: Id
    specialty_id: Id
    title: str
    bio: str
    default_room_id: Id | None
    weight: int
    last_assigned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def attach(cls, raw: Raw, *, user_id: Id, at: datetime) -> "ClinicianProfile":
        return cls._parse(
            raw, id=Id(), user_id=user_id, last_assigned_at=None, created_at=at, at=at
        )

    def edited(self, raw: Raw, *, at: datetime) -> "ClinicianProfile":
        return self._parse(
            raw,
            id=self.id,
            user_id=self.user_id,
            last_assigned_at=self.last_assigned_at,
            created_at=self.created_at,
            at=at,
        )

    @classmethod
    def _parse(
        cls,
        raw: Raw,
        *,
        id: Id,
        user_id: Id,
        last_assigned_at: datetime | None,
        created_at: datetime,
        at: datetime,
    ) -> "ClinicianProfile":
        f = RecordFields(raw)
        room = f.get("default_room_id").strip()
        default_room_id = parse_id(room) if room else None
        if room and default_room_id is None:
            f.add("default_room_id", "Choisissez une salle active de ce département.")
        profile = cls(
            id=id,
            user_id=user_id,
            department_id=f.reference("department_id", "Choisissez un département."),
            specialty_id=f.reference("specialty_id", "Choisissez une spécialité."),
            title=f.text("title", f.get("title"), max_length=100),
            bio=f.text("bio", f.get("bio"), required=False, max_length=2000),
            default_room_id=default_room_id,
            weight=f.integer("weight", f.get("weight"), minimum=1, default=DEFAULT_WEIGHT),
            last_assigned_at=last_assigned_at,
            created_at=created_at,
            updated_at=at,
        )
        f.raise_if_any()
        return profile

    @property
    def label(self) -> str:
        return self.title
