"""Fixtures of the booking scenarios; their steps live in the `steps_*` modules."""

from collections.abc import Iterator

import pytest
from django.test import Client

from drlibre.bootstrap.container import use_container
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import Scene


@pytest.fixture
def scene() -> Scene:
    return Scene()


@pytest.fixture
def web(world: FakeWorld) -> Iterator[Client]:
    """A browser stand-in served by the real pages and API over the fake wiring."""
    use_container(world.app)
    yield Client()
    use_container(None)
