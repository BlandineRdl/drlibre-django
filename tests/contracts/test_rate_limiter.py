import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
import redis
from django.conf import settings

from drlibre.identity.infrastructure.rate_limiter import RedisRateLimiter
from drlibre.shared_kernel.rate_limit import RateLimiter
from tests.fakes.clock import FixedClock
from tests.fakes.rate_limiter import InMemoryRateLimiter

WINDOW = timedelta(milliseconds=600)


@dataclass
class Limiter:
    port: RateLimiter
    wait: Callable[[timedelta], None]


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="redis", marks=pytest.mark.integration),
    ]
)
def limiter(request: pytest.FixtureRequest) -> Iterator[Limiter]:
    if request.param == "fake":
        clock = FixedClock(datetime(2026, 11, 20, 10, tzinfo=UTC))

        def advance(by: timedelta) -> None:
            clock.at += by

        yield Limiter(InMemoryRateLimiter(clock), advance)
        return
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    yield Limiter(
        RedisRateLimiter(client, prefix=prefix), lambda by: time.sleep(by.total_seconds())
    )
    for key in client.scan_iter(f"{prefix}:*"):
        client.delete(key)


def test_hits_past_the_limit_are_refused_and_counted_per_key(limiter: Limiter) -> None:
    """Story réservation provisoire : au plus 3 demandes par heure et par email."""
    port = limiter.port

    assert [port.hit("hold:email:a", limit=3, window=WINDOW) for _ in range(4)] == [
        True,
        True,
        True,
        False,
    ]
    assert port.hit("hold:email:b", limit=3, window=WINDOW)


def test_the_window_frees_attempts_once_they_age_out(limiter: Limiter) -> None:
    """Story réservation provisoire : la limite se libère avec le temps."""
    port = limiter.port
    assert port.hit("code:email:a", limit=1, window=WINDOW)
    assert not port.hit("code:email:a", limit=1, window=WINDOW)

    limiter.wait(WINDOW + timedelta(milliseconds=200))

    assert port.hit("code:email:a", limit=1, window=WINDOW)


@pytest.mark.integration
def test_redis_keys_never_hold_the_email_or_the_address() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    RedisRateLimiter(client, prefix=prefix).hit(
        "hold:email:ana@example.org", limit=3, window=WINDOW
    )

    keys = [key.decode() for key in client.scan_iter(f"{prefix}:*")]

    assert len(keys) == 1
    assert "ana" not in keys[0]
    client.delete(*keys)
