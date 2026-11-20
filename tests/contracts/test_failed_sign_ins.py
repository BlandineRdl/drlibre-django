import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import redis
from django.conf import settings

from drlibre.identity.application.ports.outbound import FailedSignIns
from drlibre.identity.domain.user import Email
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
    email = Email("ana@example.org")
    for minute in range(5):
        failures.record(email, at=AT + timedelta(minutes=minute))

    assert failures.count_since(email, since=AT) == 5
    assert failures.count_since(email, since=AT + timedelta(minutes=3)) == 2
    assert failures.count_since(Email("other@example.org"), since=AT) == 0


def test_clear_forgets_the_address(failures: FailedSignIns) -> None:
    email = Email("ana@example.org")
    failures.record(email, at=AT)

    failures.clear(email)

    assert failures.count_since(email, since=AT) == 0


@pytest.mark.integration
def test_redis_keys_never_hold_the_email() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    RedisFailedSignIns(client, prefix=prefix).record(Email("ana@example.org"), at=AT)

    keys = [key.decode() for key in client.scan_iter(f"{prefix}:*")]

    assert len(keys) == 1
    assert "ana" not in keys[0]
    client.delete(*keys)
