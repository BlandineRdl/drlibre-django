from typing import Protocol

from drlibre.health.domain.health_report import HealthReport


class CheckHealth(Protocol):
    def execute(self) -> HealthReport:
        """Report whether the application and its backing services are usable."""
        ...
