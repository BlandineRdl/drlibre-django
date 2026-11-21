import dataclasses
from dataclasses import dataclass, field
from datetime import timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.booking.application.ports.inbound import AdminAppointmentFilter, AdminAppointmentRow
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import Container, real_adapters, wire
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
)
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_booking import existing_appointment
from tests.builders_scheduling import stored_profile
from tests.use_cases.booking.steps_admin_reads import query
from tests.use_cases.booking.support import at, csv

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# The admin list rules live in the SQL: the Story is replayed on PostgreSQL.
scenarios("../features/booking/l_admin_liste_les_rdv_de_tous_les_hopitaux.feature")


@dataclass
class Db:
    app: Container = field(default_factory=lambda: wire(real_adapters()))
    type_id: Id | None = None
    room_id: Id | None = None
    patient: Id | None = None
    admin: Id | None = None
    departments: dict[str, Id] = field(default_factory=dict)
    clinicians: dict[str, Id] = field(default_factory=dict)
    named: dict[str, Appointment] = field(default_factory=dict)
    listed: Page[AdminAppointmentRow] | None = None
    error: DomainError | None = None

    def page(self) -> Page[AdminAppointmentRow]:
        assert self.listed is not None, self.error
        return self.listed


@pytest.fixture
def db() -> Db:
    return Db()


def ids(db: Db, raw: str) -> AdminAppointmentFilter:
    q = query(raw)
    department, clinician = q.get("department"), q.get("clinician")
    return AdminAppointmentFilter.from_query(
        start=q.get("start"),
        end=q.get("end"),
        department=str(db.departments[department]) if department in db.departments else department,
        clinician=str(db.clinicians[clinician]) if clinician in db.clinicians else clinician,
        status=q.get("status"),
        source=q.get("source"),
    )


def add(db: Db, clinician: str, start: str, status: str, source: str) -> Appointment:
    assert db.patient is not None
    appointment = existing_appointment(
        patient_id=db.patient,
        clinician_id=db.clinicians[clinician],
        appointment_type_id=db.type_id,
        start=at(start),
        end=at(start) + timedelta(minutes=30),
        room_id=db.room_id,
        status=AppointmentStatus(status),
        source=Source(source),
    )
    DjangoAppointments().add(appointment)
    return appointment


@given("a department with an online appointment type of 30 minutes needing a room")
def a_type(db: Db) -> None:
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    kind = build.appointment_type(department.id)
    DjangoAppointmentTypes().save(kind)
    room = build.room(department.id)
    DjangoRooms().save(room)
    db.type_id, db.room_id = kind.id, room.id


@given(parsers.parse('rooms "{names}" in that department'))
def rooms(names: str) -> None:
    """The type's room stands for them all."""


@given(
    parsers.re(
        r'an active clinician "(?P<name>[^"]+)"( with default room "[^"]+")? in that department'
    )
)
def a_clinician(name: str) -> None:
    """The clinician is placed by the hospital they work at."""


@given("a signed-in patient")
def a_patient(db: Db) -> None:
    db.patient = stored_user(Role.PATIENT).id


@given("a signed-in admin")
def an_admin(db: Db) -> None:
    db.admin = stored_user(Role.ADMIN).id


@given(parsers.parse('"{name}" works in "{department}" at "{hospital}" in "{zone}"'))
def works_in(db: Db, name: str, department: str, hospital: str, zone: str) -> None:
    place = dataclasses.replace(build.hospital(name=hospital), time_zone=zone)
    DjangoHospitals().save(place)
    unit = build.department(place.id, name=department)
    DjangoDepartments().save(unit)
    db.departments[department] = unit.id
    user = dataclasses.replace(stored_user(Role.CLINICIAN), full_name=f"Dr {name}")
    DjangoUsers().save(user)
    db.clinicians[name] = stored_profile(unit, user_id=user.id).id


@given("these appointments")
def these_appointments(db: Db, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        r = dict(zip(header, row, strict=True))
        db.named[r["name"]] = add(db, r["clinician"], r["start"], r["status"], r["source"])


@given(
    parsers.parse('{count:d} more "{status}" appointments of "{name}" one day apart from "{start}"')
)
def more(db: Db, count: int, status: str, name: str, start: str) -> None:
    for day in range(count):
        add(
            db, name, (at(start) + timedelta(days=day)).strftime("%Y-%m-%d %H:%M"), status, "ONLINE"
        )


@when(parsers.re(r'the admin lists the appointments with "(?P<raw>[^"]*)"$'))
def lists(db: Db, raw: str) -> None:
    assert db.admin is not None
    page = query(raw).get("page")
    db.listed = db.app.list_all_appointments.execute(
        actor_id=db.admin,
        appointment_filter=ids(db, raw),
        request=PageRequest.from_query(page=page, search=None),
    )


@when("the patient lists every appointment")
def patient_lists(db: Db) -> None:
    assert db.patient is not None
    try:
        db.app.list_all_appointments.execute(
            actor_id=db.patient, appointment_filter=AdminAppointmentFilter(), request=PageRequest()
        )
    except DomainError as error:
        db.error = error


def names(db: Db) -> list[str]:
    by_id = {a.id: name for name, a in db.named.items()}
    return [by_id.get(row.appointment.id, "?") for row in db.page().items]


@then(
    parsers.re(r'the list shows "(?P<shown>[^"]*)" out of (?P<total>\d+)$'),
    converters={"total": int},
)
def shows(db: Db, shown: str, total: int) -> None:
    assert names(db) == ([] if not shown else csv(shown))
    assert db.page().total == total


@then(parsers.parse("the list shows {count:d} appointments, the latest first, out of {total:d}"))
def latest_first(db: Db, count: int, total: int) -> None:
    starts = [row.appointment.start for row in db.page().items]
    assert (len(starts), db.page().total) == (count, total)
    assert starts == sorted(starts, reverse=True)


@then(parsers.parse('the list ends with "{shown}"'))
def ends_with(db: Db, shown: str) -> None:
    expected = csv(shown)
    assert names(db)[-len(expected) :] == expected


@then(parsers.parse('the row "{name}" is in "{zone}" at "{hospital}"'))
def row_zone(db: Db, name: str, zone: str, hospital: str) -> None:
    (row,) = [r for r in db.page().items if r.appointment.id == db.named[name].id]
    assert (row.time_zone, row.hospital_name) == (zone, hospital)


@then(parsers.parse('the booking is refused as "{code}"'))
def refused(db: Db, code: str) -> None:
    assert db.error is not None
    assert db.error.code.value == code
