"""Steps of an admin reading appointments, the export, the journal and running reminders."""

import dataclasses
import html
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qs

import pytest
from django.test import Client
from pytest_bdd import given, parsers, then, when

from drlibre.audit.application.ports.inbound import AuditQueries, AuditRow, JournalQuery
from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    ExportRow,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.identity.domain.user import Role
from drlibre.interfaces.web.presenters.console_appointments import csv_cell
from drlibre.interfaces.web.presenters.console_settings import REMINDERS_URL
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest
from tests.builders_booking import existing_appointment
from tests.fakes.booking import AdminClinician
from tests.fakes.world import FakeWorld
from tests.use_cases.booking.steps_waitlist import actor, add_user
from tests.use_cases.booking.support import (
    VISIT_REASON,
    Scene,
    at,
    csv,
    open_session,
    page_text,
)

EXPORT_COLUMNS = (
    "id, start, end, status, source, patient_id, clinician_id, department_id,"
    " appointment_type_id, room_id"
)


@dataclass
class AdminReads:
    departments: dict[str, Id] = field(default_factory=dict)
    named: dict[str, Appointment] = field(default_factory=dict)
    listed: Page[AdminAppointmentRow] | None = None
    exported: tuple[ExportRow, ...] = ()
    journal: Page[AuditRow] | None = None
    reminded: int | None = None

    def page(self) -> Page[AdminAppointmentRow]:
        assert self.listed is not None
        return self.listed

    def entries(self) -> Page[AuditRow]:
        assert self.journal is not None
        return self.journal


@pytest.fixture
def reads() -> AdminReads:
    return AdminReads()


def query(raw: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(raw).items()}


def appointment_filter(scene: Scene, reads: AdminReads, raw: str) -> AdminAppointmentFilter:
    q = query(raw)
    # Names of the scene stand for ids; anything else reaches the parser as typed.
    department = q.get("department")
    clinician = q.get("clinician")
    return AdminAppointmentFilter.from_query(
        start=q.get("start"),
        end=q.get("end"),
        department=str(reads.departments[department])
        if department in reads.departments
        else department,
        clinician=str(scene.clinicians[clinician]) if clinician in scene.clinicians else clinician,
        status=q.get("status"),
        source=q.get("source"),
    )


def add_appointment(
    world: FakeWorld, scene: Scene, clinician: str, start: str, status: str, source: str
) -> Appointment:
    appointment = existing_appointment(
        patient_id=scene.patient,
        clinician_id=scene.clinicians[clinician],
        appointment_type_id=scene.type,
        start=at(start),
        end=at(start) + timedelta(minutes=30),
        room_id=scene.rooms.get("R1"),
        status=AppointmentStatus(status),
        source=Source(source),
        reason=VISIT_REASON,
    )
    world.booking_appointments.rows.append(appointment)
    return appointment


@given(parsers.parse('"{name}" works in "{department}" at "{hospital}" in "{zone}"'))
def works_in(
    world: FakeWorld,
    scene: Scene,
    reads: AdminReads,
    name: str,
    department: str,
    hospital: str,
    zone: str,
) -> None:
    department_id = reads.departments.setdefault(department, Id())
    world.admin_appointments.clinicians[scene.clinicians[name]] = AdminClinician(
        name=f"Dr {name}",
        department_id=department_id,
        department=department,
        hospital_name=hospital,
        time_zone=zone,
    )


@given("these appointments")
def these_appointments(
    world: FakeWorld, scene: Scene, reads: AdminReads, datatable: list[list[str]]
) -> None:
    header, *rows = datatable
    for row in rows:
        r = dict(zip(header, row, strict=True))
        reads.named[r["name"]] = add_appointment(
            world, scene, r["clinician"], r["start"], r["status"], r["source"]
        )


@given(
    parsers.parse('{count:d} more "{status}" appointments of "{name}" one day apart from "{start}"')
)
def more_appointments(
    world: FakeWorld, scene: Scene, count: int, status: str, name: str, start: str
) -> None:
    first = at(start)
    for day in range(count):
        when_ = (first + timedelta(days=day)).strftime("%Y-%m-%d %H:%M")
        add_appointment(world, scene, name, when_, status, "ONLINE")


@when(parsers.re(r'the admin lists the appointments with "(?P<raw>[^"]*)"$'))
def admin_lists(world: FakeWorld, scene: Scene, reads: AdminReads, raw: str) -> None:
    reads.listed = world.app.list_all_appointments.execute(
        actor_id=actor(scene),
        appointment_filter=appointment_filter(scene, reads, raw),
        request=PageRequest.from_query(page=query(raw).get("page"), search=None),
    )


@when("the patient lists every appointment")
def patient_lists(world: FakeWorld, scene: Scene) -> None:
    try:
        world.app.list_all_appointments.execute(
            actor_id=scene.patient,
            appointment_filter=AdminAppointmentFilter(),
            request=PageRequest(),
        )
    except DomainError as error:
        scene.error = error


def names(reads: AdminReads) -> list[str]:
    by_id = {a.id: name for name, a in reads.named.items()}
    return [by_id.get(row.appointment.id, "?") for row in reads.page().items]


@then(
    parsers.re(r'the list shows "(?P<shown>[^"]*)" out of (?P<total>\d+)$'),
    converters={"total": int},
)
def list_shows(reads: AdminReads, shown: str, total: int) -> None:
    assert names(reads) == ([] if not shown else csv(shown))
    assert reads.page().total == total


@then(parsers.parse("the list shows {count:d} appointments, the latest first, out of {total:d}"))
def latest_first(reads: AdminReads, count: int, total: int) -> None:
    starts = [row.appointment.start for row in reads.page().items]
    assert len(starts) == count
    assert starts == sorted(starts, reverse=True)
    assert reads.page().total == total


@then(parsers.parse('the list ends with "{shown}"'))
def list_ends_with(reads: AdminReads, shown: str) -> None:
    expected = csv(shown)
    assert names(reads)[-len(expected) :] == expected


@then(parsers.parse('the row "{name}" is in "{zone}" at "{hospital}"'))
def row_zone(reads: AdminReads, name: str, zone: str, hospital: str) -> None:
    (row,) = [r for r in reads.page().items if r.appointment.id == reads.named[name].id]
    assert (row.time_zone, row.hospital_name) == (zone, hospital)


@when(parsers.re(r'the admin exports the appointments with "(?P<raw>[^"]*)"$'))
def admin_exports(world: FakeWorld, scene: Scene, reads: AdminReads, raw: str) -> None:
    reads.exported = world.app.export_appointments.execute(
        actor_id=actor(scene), appointment_filter=appointment_filter(scene, reads, raw)
    )


@when("the patient exports every appointment")
def patient_exports(world: FakeWorld, scene: Scene) -> None:
    try:
        world.app.export_appointments.execute(
            actor_id=scene.patient, appointment_filter=AdminAppointmentFilter()
        )
    except DomainError as error:
        scene.error = error


@then(parsers.parse('the export holds {count:d} rows of the columns "{columns}"'))
def export_columns(reads: AdminReads, count: int, columns: str) -> None:
    assert columns == EXPORT_COLUMNS
    assert len(reads.exported) == count
    assert [f.name for f in dataclasses.fields(ExportRow)] == csv(columns)


@then("each exported row carries the ids of its appointment")
def export_ids(world: FakeWorld, reads: AdminReads) -> None:
    for row in reads.exported:
        stored = world.booking_appointments.get(row.id)
        assert stored is not None
        who = world.admin_appointments.clinicians[stored.clinician_id]
        assert (row.patient_id, row.clinician_id, row.appointment_type_id, row.room_id) == (
            stored.patient_id,
            stored.clinician_id,
            stored.appointment_type_id,
            stored.room_id,
        )
        assert (row.department_id, row.start, row.end) == (
            who.department_id,
            stored.start,
            stored.end,
        )


@then("every exported instant is in UTC")
def export_utc(reads: AdminReads) -> None:
    instants = [i for row in reads.exported for i in (row.start, row.end)]
    assert instants
    assert all(i.utcoffset() == timedelta(0) for i in instants)


@then("no exported value is a name, a reason or a cancellation reason")
def export_no_free_text(reads: AdminReads) -> None:
    values: list[Any] = [
        getattr(row, f.name) for row in reads.exported for f in dataclasses.fields(row)
    ]
    assert values
    # Only ids, instants and closed codes: never free text.
    assert all(v is None or isinstance(v, (Id, datetime, StrEnum)) for v in values)


@then(parsers.parse('the audit entry "{action}" has the admin as actor and counts {count:d}'))
def audited_count_by_admin(world: FakeWorld, scene: Scene, action: str, count: int) -> None:
    entries = [e for e in world.audit.entries if e.action == action]
    assert [(e.actor, dict(e.metadata)) for e in entries] == [(actor(scene), {"count": count})]


@then(parsers.parse('the audit holds no "{action}"'))
def audit_holds_no(world: FakeWorld, action: str) -> None:
    assert action not in world.audit.actions()


@given("these audit entries")
def these_audit_entries(world: FakeWorld, scene: Scene, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        r = dict(zip(header, row, strict=True))
        record(
            world,
            scene.people[r["actor"]] if r["actor"] else None,
            r["action"],
            r["entity"],
            at(r["at"]),
            r["correlation"],
        )


def record(
    world: FakeWorld, who: Id | None, action: str, entity: str, when_: datetime, correlation: str
) -> None:
    world.audit.entries.append(
        AuditEntry.from_event(
            actor=who, action=action, entity_type=entity, entity_id=Id(), at=when_, metadata={}
        )
    )
    world.audit.correlation_ids.append(correlation)


@given(parsers.parse('{count:d} more audit entries one minute apart from "{start}"'))
def more_audit_entries(world: FakeWorld, scene: Scene, count: int, start: str) -> None:
    for minute in range(count):
        when_ = at(start) + timedelta(minutes=minute)
        record(world, actor(scene), "hospital.updated", "hospital", when_, f"bulk-{minute}")


@when(parsers.re(r'the admin reads the journal with "(?P<raw>[^"]*)"$'))
def admin_reads_journal(world: FakeWorld, scene: Scene, reads: AdminReads, raw: str) -> None:
    q = query(raw)
    reads.journal = world.app.view_audit_journal.execute(
        actor_id=actor(scene),
        query=JournalQuery(
            email=q.get("actor"),
            entity_type=q.get("entity_type"),
            start=q.get("start"),
            end=q.get("end"),
            request=PageRequest.from_query(page=q.get("page"), search=None),
        ),
    ).page


@then("reading the journal is forbidden")
def journal_forbidden(world: FakeWorld, scene: Scene) -> None:
    with pytest.raises(DomainError) as refused:
        admin_reads_journal(world, scene, AdminReads(), "")
    assert refused.value.code is ErrorCode.FORBIDDEN


@then("the journal offers no way to change or delete an entry")
def journal_read_only() -> None:
    def public(port: type) -> set[str]:
        return {name for name in vars(port) if not name.startswith("_")}

    assert public(AuditQueries) == {"has_acted", "entries_for", "page", "entity_types"}
    assert public(AuditLog) == {"record"}


@then(parsers.parse("the journal shows {count:d} entries, the newest first, out of {total:d}"))
def journal_newest_first(reads: AdminReads, count: int, total: int) -> None:
    ats = [row.at for row in reads.entries().items]
    assert len(ats) == count
    assert ats == sorted(ats, reverse=True)
    assert reads.entries().total == total


@then(
    parsers.re(r'the journal shows the correlations "(?P<shown>[^"]*)" out of (?P<total>\d+)$'),
    converters={"total": int},
)
def journal_correlations(reads: AdminReads, shown: str, total: int) -> None:
    shown_ids = [row.correlation_id for row in reads.entries().items]
    assert [c for c in shown_ids if not c.startswith("bulk-")] == ([] if not shown else csv(shown))
    assert reads.entries().total == total


def journal_row(reads: AdminReads, correlation: str) -> AuditRow:
    (row,) = [r for r in reads.entries().items if r.correlation_id == correlation]
    return row


@then(
    parsers.parse(
        'the entry "{correlation}" shows "{when_}", the actor "{email}", the action "{action}"'
        ' and the entity "{entity}"'
    )
)
def journal_entry(
    scene: Scene,
    reads: AdminReads,
    correlation: str,
    when_: str,
    email: str,
    action: str,
    entity: str,
) -> None:
    row = journal_row(reads, correlation)
    assert (row.at, row.actor_id, row.action, row.entity_type) == (
        at(when_),
        scene.people[email],
        action,
        entity,
    )
    assert row.entity_id is not None


@then(parsers.parse('the entries "{correlations}" show no actor'))
def journal_no_actor(reads: AdminReads, correlations: str) -> None:
    assert [journal_row(reads, c).actor_id for c in csv(correlations)] == [None, None]


@given(parsers.parse('a signed-in "{role}" user'))
def signed_in_role(world: FakeWorld, scene: Scene, role: str) -> None:
    scene.actor = add_user(world, scene, f"{role.lower()}-user@example.org", Role(role))


@when("the admin runs the reminder job")
def admin_runs_reminders(world: FakeWorld, scene: Scene, reads: AdminReads) -> None:
    reads.reminded = world.app.run_reminders.execute(actor_id=actor(scene))


@when("the admin runs the reminder job twice")
def admin_runs_reminders_twice(world: FakeWorld, scene: Scene, reads: AdminReads) -> None:
    world.app.run_reminders.execute(actor_id=actor(scene))
    reads.reminded = world.app.run_reminders.execute(actor_id=actor(scene))


@when("that user runs the reminder job")
def user_runs_reminders(world: FakeWorld, scene: Scene) -> None:
    try:
        world.app.run_reminders.execute(actor_id=actor(scene))
    except DomainError as error:
        scene.error = error


@then(parsers.parse("the admin is told {count:d} reminders were sent"))
def told_reminders(reads: AdminReads, count: int) -> None:
    assert reads.reminded == count


@when("the admin opens the settings page")
def admin_opens_settings(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, actor(scene))
    scene.page = web.get("/console/settings/")


@then("the settings page shows, with nothing to edit")
def settings_read_only(scene: Scene, datatable: list[list[str]]) -> None:
    assert scene.page.status_code == 200, scene.page.content
    body = html.unescape(page_text(scene))
    for label, value in datatable[1:]:
        assert f"<dt>{label}</dt><dd>{value}</dd>" in body
    # The page's only form runs the reminders; no field edits a rule.
    content = body[body.index("<h1>Réglages</h1>") : body.index("</main>")]
    assert content.count("<form") == 1
    assert f'action="{REMINDERS_URL}"' in content
    assert "<select" not in content
    assert "<textarea" not in content
    assert content.count("<input") == content.count('name="csrfmiddlewaretoken"')


@when(parsers.re(r"(the admin|that user) posts to the reminder job"))
def posts_reminder_job(world: FakeWorld, scene: Scene, web: Client) -> None:
    open_session(world, web, actor(scene))
    scene.page = web.post("/api/v1/jobs/reminders", "{}", content_type="application/json")


@then(parsers.parse("the API answers 200 with {count:d} reminders sent"))
def api_reminders_sent(scene: Scene, count: int) -> None:
    assert scene.page.status_code == 200, scene.page.content
    assert scene.page.json() == {"count": count}


@when(parsers.parse('a cell "{value}" is exported'))
def cell_exported(scene: Scene, value: str) -> None:
    scene.view = csv_cell(value)


@then(parsers.parse('the exported cell reads "{cell}"'))
def exported_cell(scene: Scene, cell: str) -> None:
    assert scene.view == cell
