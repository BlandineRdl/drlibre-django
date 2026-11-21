import dataclasses
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.identity.application.ports.inbound import PatientLookup
from drlibre.identity.application.ports.outbound import Sessions, Users
from drlibre.identity.domain.session import Session
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.repositories import DjangoSessions, DjangoUsers
from drlibre.shared_kernel.ids import Id
from tests.fakes.sessions import InMemorySessions
from tests.fakes.user_queries import InMemoryUserQueries
from tests.fakes.users import InMemoryUsers

AT = datetime(2026, 11, 20, 10, tzinfo=UTC)
REAL = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def stores(request: pytest.FixtureRequest) -> tuple[Users, Sessions]:
    if request.param == "fake":
        return InMemoryUsers(), InMemorySessions()
    return DjangoUsers(), DjangoSessions()


def a_user(*, password_hash: str | None = "hash") -> User:
    return User(
        id=Id(),
        email=Email(f"user-{uuid.uuid4().hex[:8]}@example.org"),
        full_name="Ana Bel",
        role=Role.CLINICIAN,
        active=True,
        password_hash=password_hash,
        must_change_password=True,
        last_login_at=None,
        created_at=AT,
        updated_at=AT,
    )


def test_saved_user_is_found_by_id_and_email(stores: tuple[Users, Sessions]) -> None:
    users, _ = stores
    user = a_user(password_hash=None)

    users.save(user)

    assert users.get(user.id) == user
    assert users.by_email(user.email) == user
    assert users.get(Id()) is None


def test_saving_again_replaces_the_user(stores: tuple[Users, Sessions]) -> None:
    users, _ = stores
    user = a_user()
    users.save(user)

    users.save(dataclasses.replace(user, full_name="Ana Belle", active=False))

    assert users.get(user.id) == dataclasses.replace(user, full_name="Ana Belle", active=False)


def test_clearing_the_phone_and_the_birth_date_is_kept(stores: tuple[Users, Sessions]) -> None:
    """Story « met à jour son profil » : un champ vide efface la valeur."""
    users, _ = stores
    user = dataclasses.replace(a_user(), phone="0601020304", birth_date=date(1990, 5, 17))
    users.save(user)

    users.save(dataclasses.replace(user, phone=None, birth_date=None))

    found = users.get(user.id)
    assert found is not None
    assert (found.phone, found.birth_date) == (None, None)


def test_sessions_are_found_by_token_hash_extended_and_deleted(
    stores: tuple[Users, Sessions],
) -> None:
    users, sessions = stores
    user = a_user()
    users.save(user)
    first = Session.after_password(
        token=uuid.uuid4().hex, user_id=user.id, role=user.role, user_agent="ua", at=AT
    )
    second = Session.after_password(
        token=uuid.uuid4().hex, user_id=user.id, role=user.role, user_agent="ua", at=AT
    )
    sessions.add(first)
    sessions.add(second)

    sessions.save(first.extended(at=AT + timedelta(days=4)))
    assert sessions.by_token_hash(first.token_hash) == first.extended(at=AT + timedelta(days=4))

    sessions.delete(first.id)
    assert sessions.by_token_hash(first.token_hash) is None
    assert sessions.delete_for_user(user.id) == 1
    assert sessions.by_token_hash(second.token_hash) is None


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def lookup(request: pytest.FixtureRequest) -> tuple[Users, PatientLookup]:
    if request.param == "fake":
        users = InMemoryUsers()
        return users, InMemoryUserQueries(users)
    return DjangoUsers(), DjangoUserQueries()


def test_the_admin_finds_active_patients_by_name_or_email_by_name(
    lookup: tuple[Users, PatientLookup],
) -> None:
    """Story L'admin réserve un RDV pour un patient : le patient est choisi parmi les actifs."""
    users, patients = lookup
    tag = uuid.uuid4().hex[:8]

    def saved(name: str, *, role: Role = Role.PATIENT, active: bool = True) -> User:
        user = dataclasses.replace(
            a_user(),
            email=Email(f"{name.split()[0].lower()}-{tag}@example.org"),
            full_name=f"{name} {tag}",
            role=role,
            active=active,
        )
        users.save(user)
        return user

    zoe, ana = saved("Zoé Roux"), saved("Ana Petit")
    saved("Inès Inactive", active=False)
    saved("Paul Praticien", role=Role.CLINICIAN)

    by_name = patients.active_patients(f"  {tag.upper()} ")
    by_email = patients.active_patients(f"zoé-{tag}@")

    assert [m.user_id for m in by_name] == [ana.id, zoe.id]
    assert [(m.full_name, m.email) for m in by_email] == [(zoe.full_name, zoe.email.value)]


def test_at_most_twenty_patients_are_found(lookup: tuple[Users, PatientLookup]) -> None:
    """Story L'admin réserve un RDV pour un patient : la recherche rend 20 patients au plus."""
    users, patients = lookup
    tag = uuid.uuid4().hex[:8]
    for number in range(21):
        user = dataclasses.replace(
            a_user(),
            email=Email(f"p{number}-{tag}@example.org"),
            full_name=f"Patient {number:02d} {tag}",
            role=Role.PATIENT,
        )
        users.save(user)

    assert len(patients.active_patients(tag)) == 20
