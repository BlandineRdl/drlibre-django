from datetime import datetime

from drlibre.identity.application.ports.outbound import FailedSignIns
from drlibre.identity.domain.user import Email


class InMemoryFailedSignIns(FailedSignIns):
    def __init__(self) -> None:
        self.failures: dict[str, list[datetime]] = {}

    def record(self, email: Email, *, at: datetime) -> None:
        self.failures.setdefault(email.value, []).append(at)

    def count_since(self, email: Email, *, since: datetime) -> int:
        return sum(1 for at in self.failures.get(email.value, []) if at >= since)

    def clear(self, email: Email) -> None:
        self.failures.pop(email.value, None)
