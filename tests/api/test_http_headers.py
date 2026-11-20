import io
import json
import logging
from collections.abc import Iterator

import pytest
import structlog
from django.test import Client

from config.logging import json_formatter

pytestmark = pytest.mark.usefixtures("fake_container")


@pytest.fixture
def request_log() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(json_formatter())
    logger = logging.getLogger("drlibre.request")
    logger.addHandler(handler)
    yield stream
    logger.removeHandler(handler)


def test_valid_correlation_id_is_echoed_and_logged(
    client: Client, request_log: io.StringIO
) -> None:
    response = client.get("/api/v1/health?token=secret", headers={"x-correlation-id": "abc"})

    assert response["x-correlation-id"] == "abc"
    line = json.loads(request_log.getvalue().splitlines()[-1])
    assert line["correlation_id"] == "abc"
    assert line["path"] == "/api/v1/health"
    assert line["status"] == 200
    assert "secret" not in request_log.getvalue()


@pytest.mark.parametrize(
    "headers",
    [{}, {"x-correlation-id": "bad\u0007id"}, {"x-correlation-id": "a" * 129}],
    ids=["missing", "non-printable", "too-long"],
)
def test_missing_or_invalid_correlation_id_is_replaced_by_a_uuid4(
    client: Client, headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/health", headers=headers)

    returned = response["x-correlation-id"]
    assert returned != headers.get("x-correlation-id")
    assert returned.count("-") == 4
    assert returned[14] == "4"


def test_responses_carry_security_headers(client: Client) -> None:
    response = client.get("/api/v1/health")

    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert "default-src 'self'" in response["Content-Security-Policy"]
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"


def test_context_does_not_leak_between_requests(client: Client) -> None:
    client.get("/api/v1/health", headers={"x-correlation-id": "first"})

    assert structlog.contextvars.get_contextvars() == {}
