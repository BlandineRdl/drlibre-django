import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Id:
    value: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def parse(cls, raw: str) -> "Id":
        return cls(uuid.UUID(raw))

    def __str__(self) -> str:
        return str(self.value)
