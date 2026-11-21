import hashlib
import uuid
from datetime import timedelta

import redis
from django.conf import settings

from drlibre.shared_kernel.rate_limit import RateLimiter

# Trim, count and add in one step, on the server's own clock, so concurrent hits cannot overshoot.
_HIT = """
local now = redis.call('TIME')
local ms = now[1] * 1000 + math.floor(now[2] / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ms - ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
  return 0
end
redis.call('ZADD', KEYS[1], ms, ARGV[3])
redis.call('PEXPIRE', KEYS[1], ARGV[1])
return 1
"""


class RedisRateLimiter(RateLimiter):
    def __init__(self, client: redis.Redis | None = None, *, prefix: str = "drlibre:rate") -> None:
        self._client = client
        self._prefix = prefix
        self._script = None

    def hit(self, key: str, *, limit: int, window: timedelta) -> bool:
        client = self._redis()
        if self._script is None:
            self._script = client.register_script(_HIT)
        # No email or address in Redis: the key is a hash of what is limited.
        hashed = hashlib.sha256(key.encode()).hexdigest()
        window_ms = int(window.total_seconds() * 1000)
        allowed = self._script(
            keys=[f"{self._prefix}:{hashed}"], args=[window_ms, limit, uuid.uuid4().hex]
        )
        return bool(allowed)

    def _redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(settings.REDIS_URL)
        return self._client
