import dataclasses
from dataclasses import dataclass

import pytest

from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    Departments,
    Hospitals,
    Rooms,
    ScheduleDependents,
    Specialties,
)
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
    DjangoSpecialties,
)
from drlibre.organisation.infrastructure.schedule_and_booking_dependents import (
    ScheduleAndBookingDependents,
)
from drlibre.scheduling.infrastructure.queries import DjangoAvailabilityQueries
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.fakes.organisation import (
    InMemoryAppointmentTypes,
    InMemoryDepartments,
    InMemoryHospitals,
    InMemoryRooms,
    InMemoryScheduleDependents,
    InMemorySpecialties,
)

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Stores:
    hospitals: Hospitals
    specialties: Specialties
    departments: Departments
    rooms: Rooms
    appointment_types: AppointmentTypes
    schedule: ScheduleDependents


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def stores(request: pytest.FixtureRequest) -> Stores:
    if request.param == "fake":
        return Stores(
            InMemoryHospitals(),
            InMemorySpecialties(),
            InMemoryDepartments(),
            InMemoryRooms(),
            InMemoryAppointmentTypes(),
            InMemoryScheduleDependents(),
        )
    return Stores(
        DjangoHospitals(),
        DjangoSpecialties(),
        DjangoDepartments(),
        DjangoRooms(),
        DjangoAppointmentTypes(),
        ScheduleAndBookingDependents(
            usage=DjangoAvailabilityQueries(), appointments=DjangoBookingQueries()
        ),
    )


def test_records_round_trip_and_update(stores: Stores) -> None:
    hospital = build.hospital()
    stores.hospitals.save(hospital)
    renamed = dataclasses.replace(hospital, name="Hôpital du Nord", longitude=3.06)

    stores.hospitals.save(renamed)

    assert stores.hospitals.get(hospital.id) == renamed
    assert stores.hospitals.get(Id()) is None


def test_codes_are_checked_against_other_records_only(stores: Stores) -> None:
    specialty = build.specialty()
    stores.specialties.save(specialty)

    assert stores.specialties.code_taken(specialty.code, except_id=Id()) is True
    assert stores.specialties.code_taken(specialty.code, except_id=specialty.id) is False


def test_children_are_listed_by_parent_and_deleted(stores: Stores) -> None:
    hospital = build.hospital()
    stores.hospitals.save(hospital)
    department = build.department(hospital.id)
    stores.departments.save(department)
    room = build.room(department.id)
    stores.rooms.save(room)
    kind = build.appointment_type(department.id)
    stores.appointment_types.save(kind)

    assert stores.departments.for_hospital(hospital.id) == (department,)
    assert stores.rooms.for_department(department.id) == (room,)
    assert stores.appointment_types.for_department(department.id) == (kind,)
    assert room.equipment == ("ECG", "Tensiomètre")

    stores.rooms.delete(room.id)
    assert stores.rooms.get(room.id) is None


def test_unused_room_and_type_have_no_schedule_dependents(stores: Stores) -> None:
    assert stores.schedule.for_room(Id()) == ()
    assert stores.schedule.for_appointment_type(Id()) == ()
