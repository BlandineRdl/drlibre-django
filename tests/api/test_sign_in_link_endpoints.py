import dataclasses
import json
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from urllib.parse import unquote

import pytest
from django.conf import settings
from django.test import Client

from drlibre.bootstrap.container import real_adapters, use_container, wire
from drlibre.identity.domain.session import hash_token
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.django.models import SessionRecord, SignInLinkRecord
from drlibre.identity.infrastructure.outbox_link_notices import OutboxLinkNotices
from tests.builders import stored_user, unique_email
from tests.fakes.email_outbox import RecordingEmailOutbox

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME


def ask(client: Client, email: str) -> Any:
    return client.post(
        "/api/v1/auth/link", json.dumps({"email": email}), content_type="application/json"
    )


def verify(client: Client, token: str) -> Any:
    return client.post(
        "/api/v1/auth/link/verify", json.dumps({"token": token}), content_type="application/json"
    )


@pytest.fixture
def outbox() -> Iterator[RecordingEmailOutbox]:
    """The real wiring with the link email kept in memory, so the test can read the token."""
    outbox = RecordingEmailOutbox()
    adapters = dataclasses.replace(
        real_adapters(),
        link_notices=OutboxLinkNotices(outbox=outbox, public_base_url="http://localhost:8000"),
    )
    use_container(wire(adapters))
    yield outbox
    use_container(None)


def emailed_token(outbox: RecordingEmailOutbox) -> str:
    match = re.search(r"token=([^\s&]+)", outbox.queued[-1].body)
    assert match
    return unquote(match.group(1))


def test_known_and_unknown_emails_get_the_same_answer(
    client: Client, outbox: RecordingEmailOutbox
) -> None:
    patient = stored_user(Role.PATIENT, password=None)

    known = ask(client, patient.email.value)
    unknown = ask(client, unique_email("nobody"))

    assert known.status_code == unknown.status_code == 202
    assert len(outbox.queued) == 1
    assert known.content == unknown.content
    assert SignInLinkRecord.objects.filter(patient_id=patient.id.value).count() == 1


def test_a_link_token_is_exchanged_once_for_a_24_hour_session(
    client: Client, outbox: RecordingEmailOutbox
) -> None:
    patient = stored_user(Role.PATIENT, password=None)
    ask(client, patient.email.value)
    token = emailed_token(outbox)

    first = verify(client, token)
    second = verify(client, token)

    assert first.status_code == 200
    assert first.json() == {"role": "PATIENT", "home": "/portal/"}
    assert first.cookies[COOKIE]["httponly"] is True
    (session,) = SessionRecord.objects.filter(user_id=patient.id.value)
    assert session.lifetime == timedelta(hours=24)
    assert not session.extendable
    assert second.status_code == 401
    assert COOKIE not in second.cookies


def test_the_database_keeps_only_the_token_hash(
    client: Client, outbox: RecordingEmailOutbox
) -> None:
    patient = stored_user(Role.PATIENT, password=None)
    ask(client, patient.email.value)
    token = emailed_token(outbox)

    (row,) = SignInLinkRecord.objects.filter(patient_id=patient.id.value)

    assert row.token_hash == hash_token(token)
    assert token not in row.token_hash
