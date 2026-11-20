from datetime import UTC, datetime

from drlibre.shared_kernel.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)
