import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import redis
from django.conf import settings

from drlibre.identity.application.ports.outbound import FailedSignIns
from drlibre.identity.infrastructure.failed_sign_ins import RedisFailedSignIns
from tests.fakes.failed_sign_ins import InMemoryFailedSignIns

AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


@pytest.fixture(
    params=[
        pytest.param("fake", id="in-memory"),
        pytest.param("real", id="redis", marks=pytest.mark.integration),
    ]
)
def failures(request: pytest.FixtureRequest) -> Iterator[FailedSignIns]:
    if request.param == "fake":
        yield InMemoryFailedSignIns()
        return
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    yield RedisFailedSignIns(client, prefix=prefix)
    for key in client.scan_iter(f"{prefix}:*"):
        client.delete(key)


def test_failures_are_counted_since_an_instant(failures: FailedSignIns) -> None:
    for minute in range(5):
        failures.record("email:ana@example.org", at=AT + timedelta(minutes=minute))

    assert failures.count_since("email:ana@example.org", since=AT) == 5
    assert failures.count_since("email:ana@example.org", since=AT + timedelta(minutes=3)) == 2
    assert failures.count_since("network:192.0.2.1", since=AT) == 0


def test_a_forgotten_failure_no_longer_counts(failures: FailedSignIns) -> None:
    kept = failures.record("network:192.0.2.1", at=AT)
    dropped = failures.record("network:192.0.2.1", at=AT)

    failures.forget("network:192.0.2.1", dropped)
    failures.forget("network:192.0.2.1", "unknown")

    assert failures.count_since("network:192.0.2.1", since=AT) == 1
    assert kept != dropped


def test_clear_forgets_the_subject(failures: FailedSignIns) -> None:
    failures.record("email:ana@example.org", at=AT)

    failures.clear("email:ana@example.org")

    assert failures.count_since("email:ana@example.org", since=AT) == 0


@pytest.mark.integration
def test_redis_keys_never_hold_the_email_or_network() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    adapter = RedisFailedSignIns(client, prefix=prefix)
    adapter.record("email:ana@example.org", at=AT)
    adapter.record("network:192.0.2.1", at=AT)

    keys = [key.decode() for key in client.scan_iter(f"{prefix}:*")]

    assert len(keys) == 2
    assert not any("ana" in key or "192.0.2" in key for key in keys)
    client.delete(*keys)
