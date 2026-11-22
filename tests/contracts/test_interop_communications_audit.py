from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interop.application.ports.inbound import (
    AuditAction,
    AuditEventFilter,
    AuditEventQueries,
    CommunicationFilter,
    CommunicationQueries,
    CommunicationRow,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_audit_events import SqlAuditEventQueries
from drlibre.interop.infrastructure.sql_communications import SqlCommunicationQueries
from drlibre.notifications.domain.notification import Notification, NotificationKind
from drlibre.notifications.infrastructure.repositories import DjangoNotifications
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders import unique_email
from tests.builders_booking import patient_user
from tests.fakes.world import FakeWorld

REAL = [pytest.mark.integration, pytest.mark.django_db]
SENT = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Scene:
    """Anne got a reminder then a cancellation, Bruno a reminder; an admin signed Anne up."""

    anne: User
    bruno: User
    admin: User
    ids: dict[str, Id]


@dataclass(frozen=True, slots=True)
class Ports:
    communications: CommunicationQueries
    audit_events: AuditEventQueries
    save_user: Callable[[User], None]
    notify: Callable[[Notification], object]
    record: Callable[[AuditEntry], None]


def _notification(recipient: User, kind: NotificationKind, hours: int) -> Notification:
    return Notification(
        id=Id(),
        recipient_id=recipient.id,
        kind=kind,
        title=kind.value.title(),
        body="Lundi à 09:00",
        appointment_id=Id(),
        created_at=SENT + timedelta(hours=hours),
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> tuple[Ports, Scene]:
    if request.param == "fake":
        world = FakeWorld()
        app = world.app
        ports = Ports(
            app.communications,
            app.audit_events,
            world.users.save,
            world.notifications.add,
            world.audit.record,
        )
    else:
        ports = Ports(
            SqlCommunicationQueries(),
            SqlAuditEventQueries(),
            DjangoUsers().save,
            DjangoNotifications().add,
            DjangoAuditLog().record,
        )
    people = [
        patient_user(Id(), email=unique_email(name), role=role)
        for name, role in (("anne", Role.PATIENT), ("bruno", Role.PATIENT), ("admin", Role.ADMIN))
    ]
    for person in people:
        ports.save_user(person)
    anne, bruno, admin = people
    found = Scene(anne, bruno, admin, {})
    for name, recipient, kind, hours in (
        ("anne reminder", anne, NotificationKind.APPOINTMENT_REMINDER, 0),
        ("anne cancelled", anne, NotificationKind.APPOINTMENT_CANCELLED, 2),
        ("bruno reminder", bruno, NotificationKind.APPOINTMENT_REMINDER, 1),
    ):
        notification = _notification(recipient, kind, hours)
        ports.notify(notification)
        found.ids[name] = notification.id
    # A run's entries are told apart from other runs' by their unique entity.
    for action, hours in (("user.created", 0), ("auth.login_succeeded", 1)):
        ports.record(
            AuditEntry.from_event(
                actor=admin.id if action == "user.created" else anne.id,
                action=action,
                entity_type="user",
                entity_id=anne.id,
                at=SENT + timedelta(hours=hours),
                metadata={"email_domain": "example.org"},
            )
        )
    return ports, found


Fixture = tuple[Ports, Scene]


def _names(scene: Scene, rows: tuple[CommunicationRow, ...]) -> list[str]:
    by_id = {i: name for name, i in scene.ids.items()}
    return [by_id[r.id] for r in rows if r.id in by_id]


def test_a_user_reads_only_their_own_notifications(scene: Fixture) -> None:
    """Story notifications FHIR: only the recipient reads their `Communication`."""
    ports, s = scene
    mine = ports.communications.communications(
        CommunicationFilter(), Reader(ReaderKind.PATIENT, s.anne.id)
    )
    admin = Reader(ReaderKind.ADMIN, s.admin.id)

    assert _names(s, mine.items) == ["anne reminder", "anne cancelled"]
    assert mine.items[0].recipient_role == "PATIENT"
    assert ports.communications.communications(CommunicationFilter(), admin).items == ()
    assert ports.communications.communications(CommunicationFilter(), Reader.anonymous()).total == 0


def test_notifications_are_found_by_category_and_sending(scene: Fixture) -> None:
    """Story notifications FHIR: searches take `recipient`, `category` and `sent`."""
    ports, s = scene
    anne = Reader(ReaderKind.PATIENT, s.anne.id)
    search = ports.communications.communications

    assert _names(s, search(CommunicationFilter(category="APPOINTMENT_CANCELLED"), anne).items) == [
        "anne cancelled"
    ]
    later = CommunicationFilter(sent_from=SENT + timedelta(hours=1))
    assert _names(s, search(later, anne).items) == ["anne cancelled"]
    assert search(CommunicationFilter(recipient=s.bruno.id), anne).items == ()
    assert ports.communications.exists(s.ids["bruno reminder"])
    assert not ports.communications.exists(Id())


def _actions(ports: Ports, s: Scene, criteria: AuditEventFilter) -> list[str]:
    admin = Reader(ReaderKind.ADMIN, s.admin.id)
    rows = ports.audit_events.events(criteria, admin).items
    return [r.action for r in rows if r.entity_id == s.anne.id]


def test_the_admin_finds_audit_entries_by_agent_entity_action_and_date(scene: Fixture) -> None:
    """Story journal FHIR: searches take `agent`, `entity`, `entity-type`, `action` and `date`."""
    ports, s = scene

    assert _actions(ports, s, AuditEventFilter(entity=s.anne.id)) == [
        "user.created",
        "auth.login_succeeded",
    ]
    assert _actions(ports, s, AuditEventFilter(agent=s.anne.id)) == ["auth.login_succeeded"]
    assert _actions(ports, s, AuditEventFilter(actions=(AuditAction.CREATE,))) == ["user.created"]
    assert _actions(ports, s, AuditEventFilter(actions=(AuditAction.EXECUTE,))) == [
        "auth.login_succeeded"
    ]
    assert _actions(ports, s, AuditEventFilter(actions=(AuditAction.READ,))) == []
    assert _actions(ports, s, AuditEventFilter(entity_type="room", entity=s.anne.id)) == []
    assert _actions(ports, s, AuditEventFilter(at_before=SENT + timedelta(hours=1))) == [
        "user.created"
    ]


def test_an_audit_entry_names_its_actor_and_entity_roles_and_metadata(scene: Fixture) -> None:
    """Story journal FHIR: action, time, agent, entity, metadata and correlation id."""
    ports, s = scene
    admin = Reader(ReaderKind.ADMIN, s.admin.id)
    (created,) = [
        r
        for r in ports.audit_events.events(AuditEventFilter(entity=s.anne.id), admin).items
        if r.action == "user.created"
    ]

    assert (created.actor_id, created.actor_role) == (s.admin.id, "ADMIN")
    assert (created.entity_type, created.entity_role, created.at) == ("user", "PATIENT", SENT)
    assert created.metadata == (("email_domain", "example.org"),)
    assert created.correlation_id == ""
    one = ports.audit_events.events(AuditEventFilter(ids=(created.id,)), admin).items
    assert [r.id for r in one] == [created.id]


@pytest.mark.parametrize("kind", [ReaderKind.PATIENT, ReaderKind.CLINICIAN, ReaderKind.ANONYMOUS])
def test_only_the_admin_reads_the_audit_journal(scene: Fixture, kind: ReaderKind) -> None:
    """Story journal FHIR: any other user is forbidden."""
    ports, s = scene

    with pytest.raises(DomainError) as refused:
        ports.audit_events.events(AuditEventFilter(), Reader(kind, s.anne.id))

    assert refused.value.code is ErrorCode.FORBIDDEN
