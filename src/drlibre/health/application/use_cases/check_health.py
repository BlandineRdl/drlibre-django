from drlibre.health.application.ports.inbound import CheckHealth
from drlibre.health.application.ports.outbound import DatabaseProbe
from drlibre.health.domain.health_report import HealthReport
from drlibre.shared_kernel.clock import Clock


class CheckHealthUseCase(CheckHealth):
    def __init__(self, clock: Clock, database: DatabaseProbe) -> None:
        self._clock = clock
        self._database = database

    def execute(self) -> HealthReport:
        return HealthReport.from_probes(
            database_up=self._database.is_up(), checked_at=self._clock.now()
        )
