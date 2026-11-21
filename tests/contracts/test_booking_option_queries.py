import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from pytest_django import DjangoAssertNumQueries

from drlibre.booking.application.ports.inbound import BookingOptionQueries, BookingOptions
from drlibre.booking.infrastructure.booking_option_queries import SqlBookingOptionQueries
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
)
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_scheduling import stored_profile
from tests.fakes.booking_options import (
    InMemoryBookingOptionQueries,
    OptionClinician,
    OptionRoom,
    OptionType,
)

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Scene:
    queries: BookingOptionQueries
    add_place: Callable[[], Id]
    add_kind: Callable[..., Id]
    add_clinician: Callable[..., Id]
    # A room's id and label.
    add_room: Callable[..., tuple[Id, str]]


def fake_scene() -> Scene:
    queries = InMemoryBookingOptionQueries()
    default = Id()

    def add_kind(
        name: str, *, online: bool = True, active: bool = True, place: Id | None = None
    ) -> Id:
        kind = Id()
        queries.types[kind] = OptionType(name, f"Hôpital {name}", place or Id(), online, active)
        return kind

    def add_clinician(name: str, *, active: bool = True, place: Id | None = None) -> Id:
        clinician = Id()
        queries.clinicians[clinician] = OptionClinician(
            name, "Cardiologie", place or default, active
        )
        return clinician

    def add_room(place: Id, name: str, *, active: bool = True) -> tuple[Id, str]:
        room, label = Id(), f"{name} (R-{Id()})"
        queries.rooms[room] = OptionRoom(label, place, active)
        return room, label

    return Scene(queries, Id, add_kind, add_clinician, add_room)


def real_scene() -> Scene:
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    places = {department.id: department}

    def add_place() -> Id:
        place = build.department(hospital.id)
        DjangoDepartments().save(place)
        places[place.id] = place
        return place.id

    def add_kind(
        name: str, *, online: bool = True, active: bool = True, place: Id | None = None
    ) -> Id:
        if place is None:
            own = dataclasses.replace(build.hospital(name=f"Hôpital {name}"), active=active)
            DjangoHospitals().save(own)
            department_of_kind = build.department(own.id)
            DjangoDepartments().save(department_of_kind)
            place = department_of_kind.id
        kind = dataclasses.replace(build.appointment_type(place), name=name, bookable_online=online)
        DjangoAppointmentTypes().save(kind)
        return kind.id

    def add_clinician(name: str, *, active: bool = True, place: Id | None = None) -> Id:
        user = dataclasses.replace(stored_user(Role.CLINICIAN), full_name=name, active=active)
        DjangoUsers().save(user)
        return stored_profile(places[place or department.id], user_id=user.id).id

    def add_room(place: Id, name: str, *, active: bool = True) -> tuple[Id, str]:
        room = build.room(place, name=name, active=active)
        DjangoRooms().save(room)
        return room.id, room.label

    return Scene(SqlBookingOptionQueries(), add_place, add_kind, add_clinician, add_room)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    return fake_scene() if request.param == "fake" else real_scene()


def test_type_choices_are_active_types_named_with_their_hospital(scene: Scene) -> None:
    """Décision du plan : le patient ne choisit qu'un type réservable en ligne."""
    online = scene.add_kind("Bilan")
    offline = scene.add_kind("Contrôle", online=False)
    scene.add_kind("Ancien", active=False)

    patient_choices = scene.queries.type_options(online_only=True)
    admin_choices = scene.queries.type_options(online_only=False)

    assert [(o.id, o.label) for o in patient_choices] == [(online, "Bilan · Hôpital Bilan")]
    assert [o.id for o in admin_choices] == [online, offline]


def test_clinician_choices_are_active_clinicians_named_with_their_department(
    scene: Scene,
) -> None:
    claire = scene.add_clinician("Claire Petit")
    scene.add_clinician("Jean Parti", active=False)
    anne = scene.add_clinician("Anne Blanc")

    choices = scene.queries.clinician_options()

    assert [(o.id, o.label) for o in choices] == [
        (anne, "Anne Blanc · Cardiologie"),
        (claire, "Claire Petit · Cardiologie"),
    ]


def test_a_type_is_booked_with_its_department_s_active_clinicians_and_rooms(
    scene: Scene,
) -> None:
    """Story RDV pour un patient : seuls les soignants et salles actifs du service du type."""
    place, elsewhere = scene.add_place(), scene.add_place()
    kind = scene.add_kind("Suivi", place=place)
    claire = scene.add_clinician("Claire Petit", place=place)
    anne = scene.add_clinician("Anne Blanc", place=place)
    scene.add_clinician("Jean Parti", active=False, place=place)
    scene.add_clinician("Paul Ailleurs", place=elsewhere)
    second = scene.add_room(place, "Salle 2")
    first = scene.add_room(place, "Salle 1")
    scene.add_room(place, "Salle fermée", active=False)
    scene.add_room(elsewhere, "Salle 0")

    options = scene.queries.booking_options(kind)

    assert [o.id for o in options.clinicians] == [anne, claire]
    assert [(o.id, o.label) for o in options.rooms] == [first, second]
    assert scene.queries.booking_options(Id()) == BookingOptions((), ())


@pytest.mark.integration
@pytest.mark.django_db
def test_each_picklist_is_one_query(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    scene = real_scene()
    kind = scene.add_kind("Suivi")
    queries = SqlBookingOptionQueries()

    for read in (
        lambda: queries.type_options(online_only=True),
        queries.clinician_options,
        lambda: queries.booking_options(kind),
    ):
        with django_assert_num_queries(1):
            read()
