import hashlib
import uuid
from datetime import datetime

import redis
from django.conf import settings

from drlibre.identity.application.ports.outbound import FailedSignIns
from drlibre.identity.domain.user import Email

# Housekeeping only: keys outlive any lockout window, the window itself is the caller's.
_KEY_TTL_SECONDS = 24 * 3600


class RedisFailedSignIns(FailedSignIns):
    def __init__(
        self, client: redis.Redis | None = None, *, prefix: str = "drlibre:signin"
    ) -> None:
        self._client = client
        self._prefix = prefix

    def _redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(settings.REDIS_URL)
        return self._client

    def _key(self, email: Email) -> str:
        # No email in Redis: the key is a hash of the address.
        return f"{self._prefix}:{hashlib.sha256(email.value.encode()).hexdigest()}"

    def record(self, email: Email, *, at: datetime) -> None:
        key = self._key(email)
        pipe = self._redis().pipeline()
        pipe.zadd(key, {uuid.uuid4().hex: at.timestamp()})
        pipe.expire(key, _KEY_TTL_SECONDS)
        pipe.execute()

    def count_since(self, email: Email, *, since: datetime) -> int:
        return self._redis().zcount(self._key(email), since.timestamp(), "+inf")

    def clear(self, email: Email) -> None:
        self._redis().delete(self._key(email))
