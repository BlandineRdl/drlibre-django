import contextlib
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
import redis
from django.conf import settings

from drlibre.identity.application.use_cases.sign_in import SignInUseCase
from drlibre.identity.infrastructure.failed_sign_ins import RedisFailedSignIns
from drlibre.shared_kernel.errors import DomainError
from tests.fakes.password_hasher import InMemoryPasswordHasher
from tests.fakes.world import FakeWorld

TRIES = 30


class SlowHasher(InMemoryPasswordHasher):
    """Holds each check long enough for every concurrent try to reach the limits first."""

    def __init__(self) -> None:
        super().__init__()
        self._count = threading.Lock()

    def verify(self, raw: str, hashed: str | None) -> bool:
        with self._count:
            self.verifications += 1
        time.sleep(0.3)
        return False


@pytest.fixture
def prefix() -> Iterator[str]:
    client = redis.Redis.from_url(settings.REDIS_URL)
    name = f"drlibre-test:{uuid.uuid4().hex}"
    yield name
    for key in client.scan_iter(f"{name}:*"):
        client.delete(key)


@pytest.mark.integration
def test_concurrent_wrong_passwords_check_at_most_ten_passwords(prefix: str) -> None:
    """Spec §12.1: 10 failures in 15 minutes lock the address, concurrent tries included."""
    world, hasher = FakeWorld(), SlowHasher()
    sign_in = SignInUseCase(
        clock=world.clock,
        uow=world.uow,
        audit=world.audit,
        users=world.users,
        sessions=world.sessions,
        hasher=hasher,
        failures=RedisFailedSignIns(prefix=prefix),
        tokens=world.tokens,
        network_hourly_limit=1000,
    )
    start = threading.Barrier(TRIES)

    def attempt(n: int) -> None:
        start.wait()
        with contextlib.suppress(DomainError):
            sign_in.execute(
                email="ana@example.org",
                password="wrong",
                user_agent="pytest",
                network=f"192.0.2.{n}",
            )

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(TRIES)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert hasher.verifications <= 10
