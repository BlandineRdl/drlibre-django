import pytest

from drlibre.identity.application.ports.outbound import PasswordHasher
from drlibre.identity.infrastructure.password_hasher import DjangoPasswordHasher
from tests.fakes.password_hasher import InMemoryPasswordHasher


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django-argon2")]
)
def hasher(request: pytest.FixtureRequest) -> PasswordHasher:
    return InMemoryPasswordHasher() if request.param == "fake" else DjangoPasswordHasher()


def test_hash_verifies_only_its_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("correct-horse-1")

    assert hashed != "correct-horse-1"
    assert hasher.verify("correct-horse-1", hashed) is True
    assert hasher.verify("wrong-horse-1", hashed) is False


def test_missing_hash_never_verifies(hasher: PasswordHasher) -> None:
    assert hasher.verify("correct-horse-1", None) is False


def test_real_hash_is_argon2() -> None:
    assert DjangoPasswordHasher().hash("correct-horse-1").startswith("argon2$")
