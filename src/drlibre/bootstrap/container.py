from dataclasses import dataclass

from drlibre.health.application.ports.inbound import CheckHealth
from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe
from drlibre.health.infrastructure.system_clock import SystemClock
from drlibre.notifications.application.ports.outbound import Mailer
from drlibre.notifications.infrastructure.smtp_mailer import SmtpMailer


@dataclass(frozen=True, slots=True)
class Container:
    check_health: CheckHealth
    mailer: Mailer


def build_container() -> Container:
    clock = SystemClock()
    return Container(
        check_health=CheckHealthUseCase(clock=clock, database=DjangoDatabaseProbe()),
        mailer=SmtpMailer(),
    )


_current: Container | None = None


def container() -> Container:
    global _current
    if _current is None:
        _current = build_container()
    return _current


def use_container(replacement: Container | None) -> None:
    """Swap the wiring, e.g. for fakes in tests; None restores the real one."""
    global _current
    _current = replacement
