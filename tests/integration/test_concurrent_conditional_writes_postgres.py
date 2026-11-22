from collections.abc import Callable

import pytest
from django.db import transaction

from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.bootstrap.container import container
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.interfaces.fhir.mappers import directory as to
from drlibre.interfaces.fhir.mappers import directory_writes as writes
from drlibre.interfaces.fhir.schemas.directory import Organization
from drlibre.interfaces.fhir.version import version_id
from drlibre.interop.application.ports.inbound import (
    LocationFilter,
    Locked,
    OrganizationFilter,
    Reader,
    ReaderKind,
    ServiceFilter,
    SpecialtyFilter,
    WriteTarget,
)
from drlibre.interop.infrastructure.conditional_writes import DjangoConditionalWrites
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.fhir.directory_scene import django_repos
from tests.integration.bookable import bookable
from tests.integration.race import Race
from tests.integration.test_concurrent_patient_changes_postgres import booked

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def _held(race: Race, read: Callable[[], object]) -> Callable[[], str]:
    """The version read under the locks; the first writer then waits for the second."""

    def current() -> str:
        found = version_id(read())
        race.hold_first()
        return found

    return current


def test_two_updates_of_one_patient_from_one_version_save_one_and_refuse_the_other() -> None:
    """Story jeton : une mise à jour avec un `If-Match` périmé échoue en 412."""
    race = Race()
    patient = stored_user(Role.PATIENT)
    stamp = lambda: UserRecord.objects.get(pk=patient.id.value).updated_at  # noqa: E731
    expected = version_id(stamp())

    def update(phone: str) -> Callable[[], object]:
        return lambda: DjangoConditionalWrites().run(
            target=WriteTarget.user(user_id=patient.id),
            expected=expected,
            current=_held(race, stamp),
            write=lambda: container().update_profile.execute(
                user_id=patient.id, phone=phone, birth_date="1980-01-01"
            ),
        )

    outcomes = race.run(update("0611111111"), update("0622222222"))

    assert race.second_was_blocked == [True]
    assert outcomes == ["conflict", "saved"]


def test_two_note_writes_on_one_appointment_from_one_version_save_one() -> None:
    """Plan E8: an appointment is locked clinician, patient, then its row, as booking does."""
    race = Race()
    with bookable() as world:
        appointment: Appointment = booked(world)
        clinician = world.scene.clinicians[0]
        stamp = lambda: AppointmentRecord.objects.get(pk=appointment.id.value).updated_at  # noqa: E731
        expected = version_id(stamp())

        def note(text: str) -> Callable[[], object]:
            return lambda: DjangoConditionalWrites().run(
                target=WriteTarget.appointment(
                    clinician_id=clinician.id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                ),
                expected=expected,
                current=_held(race, stamp),
                write=lambda: world.app().write_clinical_notes.execute(
                    actor_id=clinician.user_id, appointment_id=appointment.id, text=text
                ),
            )

        outcomes = race.run(note("Première"), note("Seconde"))

    assert race.second_was_blocked == [True]
    assert outcomes == ["conflict", "saved"]


def test_the_write_nests_in_the_check_and_its_emails_leave_at_commit() -> None:
    """Plan E8: the use case's unit of work is a savepoint; on-commit work runs once, after."""
    sent: list[str] = []

    def write() -> None:
        with DjangoUnitOfWork():
            transaction.on_commit(lambda: sent.append("mail"))
            assert sent == []

    DjangoConditionalWrites().run(
        target=WriteTarget.user(user_id=stored_user(Role.PATIENT).id),
        expected="v1",
        current=lambda: "v1",
        write=write,
    )

    assert sent == ["mail"]


_ADMIN = Reader(ReaderKind.ADMIN)


def _reference(kind: Locked) -> tuple[Id, str, Callable[[], dict[str, str]]]:
    """A stored record of the kind, its save use case and its current console fields."""
    repos = django_repos()
    hospital = build.hospital()
    repos.hospitals.save(hospital)
    department = build.department(hospital.id)
    repos.departments.save(department)
    room = build.room(department.id)
    repos.rooms.save(room)
    service = build.appointment_type(department.id)
    repos.types.save(service)
    specialty = build.specialty()
    repos.specialties.save(specialty)
    q = container().directory_queries

    def organization(record_id: Id) -> Organization:
        return to.organization(
            q.organizations(OrganizationFilter(ids=(record_id,)), _ADMIN).items[0]
        )

    found = {
        Locked.HOSPITAL: (
            hospital.id,
            "save_hospital",
            lambda: writes.hospital_fields(organization(hospital.id)),
        ),
        Locked.DEPARTMENT: (
            department.id,
            "save_department",
            lambda: writes.department_fields(organization(department.id)),
        ),
        Locked.ROOM: (
            room.id,
            "save_room",
            lambda: writes.room_fields(
                to.location(q.locations(LocationFilter(ids=(room.id,)), _ADMIN).items[0])
            ),
        ),
        Locked.APPOINTMENT_TYPE: (
            service.id,
            "save_appointment_type",
            lambda: writes.type_fields(
                to.healthcare_service(
                    q.services(ServiceFilter(ids=(service.id,)), _ADMIN).items[0], {}
                )
            ),
        ),
        Locked.SPECIALTY: (
            specialty.id,
            "save_specialty",
            lambda: writes.specialty_fields(
                to.code_system(q.specialties(SpecialtyFilter(ids=(specialty.id,)), _ADMIN).items[0])
            ),
        ),
    }
    return found[kind]


_STAMPED = {
    Locked.HOSPITAL: HospitalRecord,
    Locked.DEPARTMENT: DepartmentRecord,
    Locked.ROOM: RoomRecord,
    Locked.APPOINTMENT_TYPE: AppointmentTypeRecord,
    Locked.SPECIALTY: SpecialtyRecord,
}


@pytest.mark.parametrize("kind", list(_STAMPED), ids=[k.value for k in _STAMPED])
def test_two_updates_of_one_reference_record_from_one_version_save_one(kind: Locked) -> None:
    """Story référentiel : un `If-Match` périmé échoue ; the record's own row is the lock."""
    race = Race()
    record_id, save, current = _reference(kind)
    stamp = lambda: _STAMPED[kind].objects.get(pk=record_id.value).updated_at  # noqa: E731
    expected = version_id(stamp())

    def update(name: str) -> Callable[[], object]:
        return lambda: DjangoConditionalWrites().run(
            target=WriteTarget.record(kind, record_id),
            expected=expected,
            current=_held(race, stamp),
            write=lambda: getattr(container(), save).execute(
                actor=None, record_id=record_id, fields=current() | {"name": name}
            ),
        )

    outcomes = race.run(update("Premier"), update("Second"))

    assert race.second_was_blocked == [True]
    assert outcomes == ["conflict", "saved"]
