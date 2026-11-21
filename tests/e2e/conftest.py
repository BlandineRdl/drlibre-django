import os
from typing import Any

import pytest

from tests.e2e.pages import reset_rate_limits


@pytest.fixture(scope="session")
def base_url() -> str:
    """The compose web service; override with E2E_BASE_URL."""
    return os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    # The CSP forbids inline scripts; bypassing it lets the vendored axe-core be injected.
    return {**browser_context_args, "bypass_csp": True, "locale": "fr-FR"}


@pytest.fixture(autouse=True)
def fresh_rate_limits() -> None:
    reset_rate_limits()
