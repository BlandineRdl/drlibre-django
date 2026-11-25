import uuid
from datetime import datetime

from drlibre.identity.application.ports.outbound import FailedSignIns


class InMemoryFailedSignIns(FailedSignIns):
    def __init__(self) -> None:
        self.failures: dict[str, dict[str, datetime]] = {}

    def record(self, subject: str, *, at: datetime) -> str:
        failure = uuid.uuid4().hex
        self.failures.setdefault(subject, {})[failure] = at
        return failure

    def count_since(self, subject: str, *, since: datetime) -> int:
        return sum(1 for at in self.failures.get(subject, {}).values() if at >= since)

    def forget(self, subject: str, failure: str) -> None:
        self.failures.get(subject, {}).pop(failure, None)

    def clear(self, subject: str) -> None:
        self.failures.pop(subject, None)
