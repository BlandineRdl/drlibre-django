import uuid
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.identity.application.ports.outbound import SignInLinks, Users
from drlibre.identity.domain.sign_in_link import SignInLink
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.repositories import DjangoSignInLinks, DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.fakes.sign_in_links import InMemorySignInLinks
from tests.fakes.users import InMemoryUsers

AT = datetime(2026, 11, 20, 10, tzinfo=UTC)
REAL = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def stores(request: pytest.FixtureRequest) -> tuple[Users, SignInLinks]:
    if request.param == "fake":
        return InMemoryUsers(), InMemorySignInLinks()
    return DjangoUsers(), DjangoSignInLinks()


def a_patient(users: Users) -> Id:
    patient = User(
        id=Id(),
        email=Email(f"patient-{uuid.uuid4().hex[:8]}@example.org"),
        full_name="Léa Martin",
        role=Role.PATIENT,
        active=True,
        password_hash=None,
        must_change_password=False,
        last_login_at=None,
        created_at=AT,
        updated_at=AT,
    )
    users.save(patient)
    return patient.id


def test_a_link_is_found_by_its_token_hash(stores: tuple[Users, SignInLinks]) -> None:
    users, links = stores
    link = SignInLink.issue(token=uuid.uuid4().hex, patient_id=a_patient(users), at=AT)

    links.add(link)

    assert links.by_token_hash(link.token_hash) == link
    assert links.by_token_hash("0" * 64) is None


def test_saving_a_used_link_replaces_it(stores: tuple[Users, SignInLinks]) -> None:
    users, links = stores
    link = SignInLink.issue(token=uuid.uuid4().hex, patient_id=a_patient(users), at=AT)
    links.add(link)

    links.save(link.used(AT + timedelta(minutes=1)))

    stored = links.by_token_hash(link.token_hash)
    assert stored is not None
    assert stored.used_at == AT + timedelta(minutes=1)


def test_cancelling_open_links_spares_used_links_and_other_patients(
    stores: tuple[Users, SignInLinks],
) -> None:
    users, links = stores
    patient, other = a_patient(users), a_patient(users)
    open_link = SignInLink.issue(token=uuid.uuid4().hex, patient_id=patient, at=AT)
    used_link = SignInLink.issue(token=uuid.uuid4().hex, patient_id=patient, at=AT).used(AT)
    elsewhere = SignInLink.issue(token=uuid.uuid4().hex, patient_id=other, at=AT)
    for link in (open_link, used_link, elsewhere):
        links.add(link)

    links.cancel_open_for(patient, at=AT + timedelta(minutes=2))

    cancelled = links.by_token_hash(open_link.token_hash)
    assert cancelled is not None
    assert cancelled.cancelled_at == AT + timedelta(minutes=2)
    assert links.by_token_hash(used_link.token_hash) == used_link
    assert links.by_token_hash(elsewhere.token_hash) == elsewhere
