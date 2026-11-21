from datetime import timedelta
from typing import Protocol


class RateLimiter(Protocol):
    def hit(self, key: str, *, limit: int, window: timedelta) -> bool:
        """Count one attempt on the key; False, counting nothing, once the window holds `limit`."""
        ...
