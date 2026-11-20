from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"


class ComponentState(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: HealthStatus
    database: ComponentState
    checked_at: datetime

    @classmethod
    def from_probes(cls, *, database_up: bool, checked_at: datetime) -> "HealthReport":
        if database_up:
            return cls(HealthStatus.OK, ComponentState.UP, checked_at)
        return cls(HealthStatus.DEGRADED, ComponentState.DOWN, checked_at)

    @property
    def is_healthy(self) -> bool:
        return self.status is HealthStatus.OK
