import pytest

from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interop.application.ports.inbound import (
    ConditionalWrites,
    StaleVersionError,
    WriteTarget,
)
from drlibre.interop.infrastructure.conditional_writes import DjangoConditionalWrites
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.fakes.interop import InMemoryConditionalWrites

REAL = [pytest.mark.integration, pytest.mark.django_db]
TARGET = WriteTarget.user(user_id=Id())


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def writes(request: pytest.FixtureRequest) -> ConditionalWrites:
    return InMemoryConditionalWrites() if request.param == "fake" else DjangoConditionalWrites()


def test_without_if_match_the_write_runs_as_is(writes: ConditionalWrites) -> None:
    """Plan E8: without If-Match, the write goes straight through."""
    assert writes.run(target=TARGET, expected=None, current=lambda: "v2", write=lambda: 1) == 1


def test_the_current_version_lets_the_write_run(writes: ConditionalWrites) -> None:
    assert writes.run(target=TARGET, expected="v1", current=lambda: "v1", write=lambda: 1) == 1


def test_a_stale_version_is_refused_before_writing(writes: ConditionalWrites) -> None:
    """Story jeton: an update with a stale If-Match fails with 412, nothing written."""
    written: list[int] = []

    with pytest.raises(StaleVersionError) as raised:
        writes.run(
            target=TARGET, expected="v1", current=lambda: "v2", write=lambda: written.append(1)
        )

    assert raised.value.code is ErrorCode.CONFLICT
    assert written == []


def test_a_refusal_of_the_write_reaches_the_caller(writes: ConditionalWrites) -> None:
    def refuse() -> None:
        raise DomainError(ErrorCode.RULE_VIOLATION, "Refusé.")

    with pytest.raises(DomainError) as raised:
        writes.run(target=TARGET, expected="v1", current=lambda: "v1", write=refuse)

    assert raised.value.code is ErrorCode.RULE_VIOLATION


def test_a_refusal_reaches_the_caller_without_if_match(writes: ConditionalWrites) -> None:
    def refuse() -> None:
        raise DomainError(ErrorCode.INVALID_INPUT, "Refusé.")

    with pytest.raises(DomainError) as raised:
        writes.run(target=TARGET, expected=None, current=lambda: "v1", write=refuse)

    assert raised.value.code is ErrorCode.INVALID_INPUT


@pytest.mark.integration
@pytest.mark.django_db
def test_a_refusal_keeps_none_of_the_writes_before_it() -> None:
    """Story disponibilités en FHIR: a refused time off period leaves none of the others written."""
    saved: list[User] = []

    def save_then_refuse() -> None:
        saved.append(stored_user(Role.PATIENT))
        raise DomainError(ErrorCode.INVALID_INPUT, "Refusé.")

    with pytest.raises(DomainError):
        DjangoConditionalWrites().run(
            target=TARGET,
            expected=None,
            current=lambda: "v1",
            write=save_then_refuse,
        )

    assert DjangoUsers().get(saved[0].id) is None
