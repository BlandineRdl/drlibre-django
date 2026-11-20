import re

import pytest

from drlibre.identity.application.ports.outbound import TokenGenerator
from drlibre.identity.infrastructure.tokens import SecretsTokenGenerator
from tests.fakes.tokens import InMemoryTokenGenerator


@pytest.fixture(params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="secrets")])
def tokens(request: pytest.FixtureRequest) -> TokenGenerator:
    return InMemoryTokenGenerator() if request.param == "fake" else SecretsTokenGenerator()


def test_each_session_gets_its_own_cookie_safe_token(tokens: TokenGenerator) -> None:
    """Spec §12.2: a session is a token in a cookie; two sessions never share one."""
    first, second = tokens.new_token(), tokens.new_token()

    assert first != second
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)


def test_real_tokens_are_long_enough_to_be_unguessable() -> None:
    assert len(SecretsTokenGenerator().new_token()) >= 40
