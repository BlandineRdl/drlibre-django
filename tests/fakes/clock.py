from datetime import datetime

from drlibre.shared_kernel.clock import Clock


class FixedClock(Clock):
    def __init__(self, at: datetime) -> None:
        self.at = at

    def now(self) -> datetime:
        return self.at
