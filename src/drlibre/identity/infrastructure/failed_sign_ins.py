import hashlib
import uuid
from datetime import datetime

import redis
from django.conf import settings

from drlibre.identity.application.ports.outbound import FailedSignIns

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

    def _key(self, subject: str) -> str:
        # No email or network address in Redis: the key is a hash of the subject.
        return f"{self._prefix}:{hashlib.sha256(subject.encode()).hexdigest()}"

    def record(self, subject: str, *, at: datetime) -> str:
        key, failure = self._key(subject), uuid.uuid4().hex
        pipe = self._redis().pipeline()
        pipe.zadd(key, {failure: at.timestamp()})
        pipe.expire(key, _KEY_TTL_SECONDS)
        pipe.execute()
        return failure

    def count_since(self, subject: str, *, since: datetime) -> int:
        return self._redis().zcount(self._key(subject), since.timestamp(), "+inf")

    def forget(self, subject: str, failure: str) -> None:
        self._redis().zrem(self._key(subject), failure)

    def clear(self, subject: str) -> None:
        self._redis().delete(self._key(subject))
