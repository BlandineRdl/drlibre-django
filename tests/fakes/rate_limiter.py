from datetime import datetime, timedelta

from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.rate_limit import RateLimiter


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.hits: dict[str, list[datetime]] = {}

    def hit(self, key: str, *, limit: int, window: timedelta) -> bool:
        now = self.clock.now()
        recent = [at for at in self.hits.get(key, []) if now - at < window]
        self.hits[key] = recent
        if len(recent) >= limit:
            return False
        recent.append(now)
        return True
