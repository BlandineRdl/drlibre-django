from datetime import timedelta
from typing import Protocol

HOURLY = timedelta(hours=1)


class RateLimiter(Protocol):
    def hit(self, key: str, *, limit: int, window: timedelta) -> bool:
        """Count one attempt on the key; False, counting nothing, once the window holds `limit`."""
        ...


def within_hourly_limits(
    limiter: RateLimiter, *, kind: str, email: str, network: str, per_email: int, per_network: int
) -> bool:
    """Count one request for the email, then the network; False once either holds its limit."""
    return limiter.hit(f"{kind}:email:{email}", limit=per_email, window=HOURLY) and limiter.hit(
        f"{kind}:network:{network}", limit=per_network, window=HOURLY
    )
