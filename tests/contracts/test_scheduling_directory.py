from dataclasses import dataclass

import pytest

from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.organisation.infrastructure.repositories import DjangoAppointmentTypes, DjangoRooms
from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    Clinician,
    Room,
    SchedulingDirectory,
)
from drlibre.scheduling.infrastructure.directory import OrganisationSchedulingDirectory
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_scheduling import stored_department, stored_profile
from tests.fakes.scheduling import FixedSchedulingDirectory

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Known:
    """One department holding an active and an inactive clinician, a type and a room."""

    directory: SchedulingDirectory
    department: Id
    active_user: Id
    active: Clinician
    inactive: Clinician
    kind: AppointmentType
    room: Room


def fake() -> Known:
    directory = FixedSchedulingDirectory()
    department, user = Id(), Id()
    active = Clinician(Id(), department, "Europe/Paris", active=True)
    inactive = Clinician(Id(), department, "Europe/Paris", active=False)
    kind = AppointmentType(Id(), department, 30, 0, active=True)
    room = Room(Id(), department, active=True)
    directory.clinicians = {active.id: active, inactive.id: inactive}
    directory.profile_of_user[user] = active.id
    directory.types[kind.id] = kind
    directory.rooms[room.id] = room
    return Known(directory, department, user, active, inactive, kind, room)


def real() -> Known:
    department = stored_department()
    user = stored_user(Role.CLINICIAN, password=None)
    gone = stored_user(Role.CLINICIAN, password=None, active=False)
    active = stored_profile(department, user_id=user.id)
    inactive = stored_profile(department, user_id=gone.id)
    kind = build.appointment_type(department.id)
    DjangoAppointmentTypes().save(kind)
    room = build.room(department.id)
    DjangoRooms().save(room)
    users = DjangoUserQueries()
    directory = OrganisationSchedulingDirectory(queries=DjangoReferenceQueries(), lookup=users)
    return Known(
        directory,
        department.id,
        user.id,
        Clinician(active.id, department.id, "Europe/Paris", active=True),
        Clinician(inactive.id, department.id, "Europe/Paris", active=False),
        AppointmentType(kind.id, department.id, 30, 0, active=True),
        Room(room.id, department.id, active=True),
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def known(request: pytest.FixtureRequest) -> Known:
    return fake() if request.param == "fake" else real()


def test_a_clinician_carries_the_time_zone_of_their_hospital(known: Known) -> None:
    """Spec §4 : les plages sont en heure locale de l'hôpital du praticien."""
    assert known.directory.clinician(known.active.id) == known.active
    assert known.directory.clinician(known.inactive.id) == known.inactive
    assert known.directory.clinician(Id()) is None


def test_the_signed_in_user_is_resolved_to_their_own_profile(known: Known) -> None:
    """Spec §4 : l'identité vient de la session, jamais du corps de la requête."""
    assert known.directory.clinician_of(known.active_user) == known.active
    assert known.directory.clinician_of(Id()) is None


def test_only_active_clinicians_of_the_department_are_listed(known: Known) -> None:
    assert known.directory.active_clinicians(known.department) == (known.active.id,)
    assert known.directory.active_clinicians(Id()) == ()


def test_types_and_rooms_of_the_department_are_read(known: Known) -> None:
    assert known.directory.appointment_type(known.kind.id) == known.kind
    assert known.directory.appointment_types(known.department) == (known.kind,)
    assert known.directory.room(known.room.id) == known.room
    assert known.directory.room(Id()) is None
