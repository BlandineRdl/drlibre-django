from dataclasses import dataclass
from datetime import datetime

from drlibre.organisation.domain.fields import Raw, RecordFields
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Hospital:
    id: Id
    name: str
    code: str
    description: str
    street: str
    postal_code: str
    city: str
    country: str
    phone: str
    time_zone: str
    latitude: float | None
    longitude: float | None
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_form(cls, raw: Raw, *, id: Id, created_at: datetime, at: datetime) -> "Hospital":
        f = RecordFields(raw)
        hospital = cls(
            id=id,
            name=f.name(),
            code=f.code(),
            description=f.text(
                "description", f.get("description"), required=False, max_length=1000
            ),
            street=f.text("street", f.get("street")),
            postal_code=f.text("postal_code", f.get("postal_code"), max_length=20),
            city=f.text("city", f.get("city"), max_length=100),
            country=f.text("country", f.get("country"), max_length=100),
            phone=f.text("phone", f.get("phone"), max_length=30),
            time_zone=f.time_zone(),
            latitude=f.optional_float("latitude", f.get("latitude"), low=-90, high=90),
            longitude=f.optional_float("longitude", f.get("longitude"), low=-180, high=180),
            active=f.flag("active"),
            created_at=created_at,
            updated_at=at,
        )
        f.raise_if_any()
        return hospital

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"
