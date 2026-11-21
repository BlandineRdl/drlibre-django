import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from pytest_django import DjangoAssertNumQueries

from drlibre.booking.application.ports.inbound import WaitlistQueries, WaitlistStatus
from drlibre.booking.application.ports.outbound import Appointments, Waitlist
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoWaitlist
from drlibre.booking.infrastructure.waitlist_queries import SqlWaitlistQueries
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_booking import existing_appointment, patient_user
from tests.builders_scheduling import stored_profile
from tests.fakes.booking import (
    InMemoryAppointments,
    InMemoryWaitlist,
    InMemoryWaitlistQueries,
    WaitlistType,
)
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass
class Scene:
    queries: WaitlistQueries
    waitlist: Waitlist
    appointments: Appointments
    add_kind: Callable[[str], Id]
    add_clinician: Callable[[str], Id]
    add_patient: Callable[[str], Id]


def fake_scene() -> Scene:
    users = InMemoryUsers()
    appointments = InMemoryAppointments()
    waitlist = InMemoryWaitlist(appointments)
    queries = InMemoryWaitlistQueries(waitlist, users)

    def add_kind(name: str) -> Id:
        kind = Id()
        queries.types[kind] = WaitlistType(name, f"Hôpital {name}", "Europe/Paris")
        return kind

    def add_clinician(name: str) -> Id:
        clinician = Id()
        queries.clinicians[clinician] = name
        return clinician

    def add_patient(name: str) -> Id:
        patient = Id()
        users.save(dataclasses.replace(patient_user(patient), full_name=name))
        return patient

    return Scene(queries, waitlist, appointments, add_kind, add_clinician, add_patient)


def real_scene() -> Scene:
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)

    def add_kind(name: str) -> Id:
        own = build.hospital(name=f"Hôpital {name}")
        DjangoHospitals().save(own)
        place = build.department(own.id)
        DjangoDepartments().save(place)
        kind = dataclasses.replace(build.appointment_type(place.id), name=name)
        DjangoAppointmentTypes().save(kind)
        return kind.id

    def add_clinician(name: str) -> Id:
        user = dataclasses.replace(stored_user(Role.CLINICIAN), full_name=name)
        DjangoUsers().save(user)
        return stored_profile(department, user_id=user.id).id

    def add_patient(name: str) -> Id:
        user = dataclasses.replace(stored_user(Role.PATIENT), full_name=name)
        DjangoUsers().save(user)
        return user.id

    return Scene(
        SqlWaitlistQueries(),
        DjangoWaitlist(),
        DjangoAppointments(),
        add_kind,
        add_clinician,
        add_patient,
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    return fake_scene() if request.param == "fake" else real_scene()


def joined(
    scene: Scene, patient: Id, kind: Id, *, minutes: int = 0, clinician: Id | None = None
) -> WaitlistEntry:
    entry = WaitlistEntry.join(
        patient_id=patient,
        appointment_type_id=kind,
        clinician_id=clinician,
        earliest=NOW,
        latest=NOW + timedelta(days=7),
        at=NOW + timedelta(minutes=minutes),
    )
    scene.waitlist.add(entry)
    return entry


def test_a_patient_sees_their_own_entries_newest_first_with_whom_and_what(scene: Scene) -> None:
    """Story inscription : le patient voit la liste de ses entrées avec leur statut."""
    lea, other = scene.add_patient("Léa Martin"), scene.add_patient("Paul Durand")
    kind = scene.add_kind("Suivi")
    clinician = scene.add_clinician("Claire Petit")
    first = joined(scene, lea, kind, clinician=clinician)
    second = joined(scene, lea, kind, minutes=5)
    joined(scene, other, kind)

    rows = scene.queries.own_entries(lea)

    assert [r.entry for r in rows] == [second, first]
    assert [r.clinician_name for r in rows] == [None, "Claire Petit"]
    assert {(r.patient_name, r.appointment_type, r.hospital_name, r.time_zone) for r in rows} == {
        ("Léa Martin", "Suivi", "Hôpital Suivi", "Europe/Paris")
    }
    assert scene.queries.own_entries(Id()) == ()


def test_an_offered_entry_shows_the_start_of_the_freed_slot(scene: Scene) -> None:
    patient, kind = scene.add_patient("Léa Martin"), scene.add_kind("Suivi")
    clinician = scene.add_clinician("Claire Petit")
    start = NOW + timedelta(days=2)
    freed = existing_appointment(
        patient_id=scene.add_patient("Paul Durand"),
        clinician_id=clinician,
        appointment_type_id=kind,
        start=start,
        end=start + timedelta(minutes=30),
        status=AppointmentStatus.CANCELLED,
    )
    scene.appointments.add(freed)
    scene.waitlist.save(joined(scene, patient, kind).offered(freed.id))

    (row,) = scene.queries.own_entries(patient)

    assert (row.entry.status, row.offered_start) == (WaitlistStatus.OFFERED, start)


def test_the_admin_list_runs_oldest_first_twenty_a_page_with_the_total(scene: Scene) -> None:
    """Story suivi : des plus anciennes aux plus récentes, par pages de 20 avec le total."""
    patient, kind = scene.add_patient("Léa Martin"), scene.add_kind("Suivi")
    entries = [joined(scene, patient, kind, minutes=m) for m in range(21)]

    first = scene.queries.page("", PageRequest(1))
    second = scene.queries.page("", PageRequest(2))
    beyond = scene.queries.page("", PageRequest(3))

    assert [r.entry.id for r in first.items] == [e.id for e in entries[:20]]
    assert [r.entry.id for r in second.items] == [entries[20].id]
    assert (first.total, second.total, beyond.total, beyond.items) == (21, 21, 21, ())


def test_the_admin_list_filters_by_status_and_ignores_an_unusable_one(scene: Scene) -> None:
    """Story suivi : un filtre inutilisable revient à la valeur par défaut."""
    patient, kind = scene.add_patient("Léa Martin"), scene.add_kind("Suivi")
    waiting = joined(scene, patient, kind)
    expired = joined(scene, patient, kind, minutes=1).expired()
    scene.waitlist.save(expired)

    only_expired = scene.queries.page("EXPIRED", PageRequest())
    everything = scene.queries.page("bogus", PageRequest())

    assert [r.entry.id for r in only_expired.items] == [expired.id]
    assert [r.entry.id for r in everything.items] == [waiting.id, expired.id]
    assert scene.queries.page("BOOKED", PageRequest()).total == 0


@pytest.mark.integration
@pytest.mark.django_db
def test_each_waitlist_read_is_one_query(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    scene = real_scene()
    patient, kind = scene.add_patient("Léa Martin"), scene.add_kind("Suivi")
    joined(scene, patient, kind)
    queries = SqlWaitlistQueries()

    for read in (
        lambda: queries.own_entries(patient),
        lambda: queries.page("WAITING", PageRequest()),
    ):
        with django_assert_num_queries(1):
            read()
