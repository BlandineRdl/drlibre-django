"""Steps of the reminder job."""

import re
from typing import Any

from pytest_bdd import given, parsers, then, when

from tests.fakes.world import FakeWorld
from tests.use_cases.booking.support import (
    VISIT_REASON,
    Scene,
    at,
    csv,
)


@given("the reminder job ran")
@when("the reminder job runs")
def reminder_job_runs(world: FakeWorld) -> None:
    world.app.send_reminders.execute()


@when("the reminder job runs twice")
def reminder_job_runs_twice(world: FakeWorld) -> None:
    reminder_job_runs(world)
    reminder_job_runs(world)


def reminder_emails(world: FakeWorld) -> list[Any]:
    return [m for m in world.outbox.queued if m.subject == "Rappel de votre rendez-vous"]


@then(parsers.parse('the patient has "{title}" notifications for the appointments at "{starts}"'))
def reminded_for(world: FakeWorld, scene: Scene, title: str, starts: str) -> None:
    by_id = {a.id: a.start for a in world.booking_appointments.rows}
    rows = [n for n in world.notifications.rows if n.recipient_id == scene.patient]
    assert all(n.title == title for n in rows)
    assert sorted(by_id[n.appointment_id] for n in rows if n.appointment_id) == [
        at(start) for start in csv(starts)
    ]


@then(parsers.parse("{count:d} reminder emails were sent"))
def reminder_emails_sent(world: FakeWorld, count: int) -> None:
    assert len(reminder_emails(world)) == count


@then(
    "each reminder email names the time, hospital and provider, without the reason,"
    " linking only to the sign-in page"
)
def reminder_content(world: FakeWorld) -> None:
    sent = reminder_emails(world)
    assert [m.to for m in sent] == [("patient@example.org",)] * 2
    for mail, local in zip(sent, ("20/11/2026 à 13:00", "21/11/2026 à 11:00"), strict=True):
        assert local in mail.body
        assert VISIT_REASON not in mail.body
        assert "Hôpital Test" in mail.body
        assert "A" in mail.body
        assert re.findall(r"https?://\S+", mail.body) == ["http://localhost:8000/sign-in"]


@then(parsers.parse('the audit entry "{action}" has no actor and counts {count:d}'))
def audit_counted(world: FakeWorld, action: str, count: int) -> None:
    (entry,) = [e for e in world.audit.entries if e.action == action]
    assert entry.actor is None
    assert dict(entry.metadata) == {"count": count}
