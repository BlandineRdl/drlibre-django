import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.application.ports.outbound import (
    AdminAppointmentFilter,
    AdminAppointments,
    Appointments,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.infrastructure.admin_appointments import SqlAdminAppointments
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_booking import existing_appointment, patient_user
from tests.builders_scheduling import stored_profile
from tests.fakes.booking import AdminClinician, InMemoryAdminAppointments, InMemoryAppointments
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]
AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Clinic:
    clinician: Id
    department: Id
    kind: Id
    room: Id


@dataclass
class Scene:
    queries: AdminAppointments
    appointments: Appointments
    add_clinic: Callable[[str, str], Clinic]
    add_patient: Callable[[str], Id]


def fake_scene() -> Scene:
    users = InMemoryUsers()
    appointments = InMemoryAppointments()
    queries = InMemoryAdminAppointments(appointments, users)

    def add_clinic(name: str, zone: str) -> Clinic:
        clinic = Clinic(Id(), Id(), Id(), Id())
        queries.clinicians[clinic.clinician] = AdminClinician(
            f"Dr {name}", clinic.department, "Cardiologie", f"Hôpital {name}", zone
        )
        queries.labels |= {clinic.kind: "Consultation", clinic.room: "Salle 1"}
        return clinic

    def add_patient(name: str) -> Id:
        patient = Id()
        users.save(dataclasses.replace(patient_user(patient), full_name=name))
        return patient

    return Scene(queries, appointments, add_clinic, add_patient)


def real_scene() -> Scene:
    def add_clinic(name: str, zone: str) -> Clinic:
        hospital = dataclasses.replace(build.hospital(name=f"Hôpital {name}"), time_zone=zone)
        DjangoHospitals().save(hospital)
        department = build.department(hospital.id)
        DjangoDepartments().save(department)
        kind = build.appointment_type(department.id)
        DjangoAppointmentTypes().save(kind)
        room = build.room(department.id)
        DjangoRooms().save(room)
        user = dataclasses.replace(stored_user(Role.CLINICIAN), full_name=f"Dr {name}")
        DjangoUsers().save(user)
        profile = stored_profile(department, user_id=user.id)
        return Clinic(profile.id, department.id, kind.id, room.id)

    def add_patient(name: str) -> Id:
        user = dataclasses.replace(stored_user(Role.PATIENT), full_name=name)
        DjangoUsers().save(user)
        return user.id

    return Scene(SqlAdminAppointments(), DjangoAppointments(), add_clinic, add_patient)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    return fake_scene() if request.param == "fake" else real_scene()


def booked(scene: Scene, clinic: Clinic, patient: Id, start: datetime) -> Appointment:
    appointment = dataclasses.replace(
        existing_appointment(
            patient_id=patient,
            clinician_id=clinic.clinician,
            appointment_type_id=clinic.kind,
            start=start,
            end=start + timedelta(minutes=30),
            room_id=clinic.room,
            source=Source.STAFF,
            reason="Douleur",
        ),
        clinical_notes="Notes du praticien",
    )
    scene.appointments.add(appointment)
    return appointment


def test_a_row_names_who_where_and_what_in_its_hospital_zone_never_the_notes(
    scene: Scene,
) -> None:
    """Story L'admin liste les RDV de tous les hôpitaux : fuseau de l'hôpital par ligne."""
    clinic = scene.add_clinic("Lamentin", "America/Martinique")
    patient = scene.add_patient("Léa Martin")
    appointment = booked(scene, clinic, patient, AT)

    (row,) = scene.queries.page(AdminAppointmentFilter(), PageRequest()).items

    assert row.appointment == dataclasses.replace(appointment, clinical_notes=None)
    assert (row.patient_name, row.clinician_name, row.department) == (
        "Léa Martin",
        "Dr Lamentin",
        "Cardiologie",
    )
    assert (row.appointment_type, row.room) == ("Consultation", "Salle 1")
    assert (row.hospital_name, row.time_zone) == ("Hôpital Lamentin", "America/Martinique")


def test_the_export_holds_ids_and_utc_instants_of_every_match_latest_first(scene: Scene) -> None:
    """Story L'admin exporte les RDV filtrés en CSV : tout l'ensemble filtré, en ids."""
    clinic = scene.add_clinic("Nord", "Europe/Paris")
    patient = scene.add_patient("Léa Martin")
    first = booked(scene, clinic, patient, AT)
    later = booked(scene, clinic, patient, AT + timedelta(days=1))

    rows = scene.queries.all(AdminAppointmentFilter(clinician_id=clinic.clinician))

    assert [r.id for r in rows] == [later.id, first.id]
    assert (rows[0].department_id, rows[0].appointment_type_id, rows[0].room_id) == (
        clinic.department,
        clinic.kind,
        clinic.room,
    )
    assert (rows[0].status, rows[0].source) == (AppointmentStatus.BOOKED, Source.STAFF)
    assert rows[0].start == later.start


def test_the_period_counts_the_local_day_of_each_hospital(scene: Scene) -> None:
    """Story L'admin liste les RDV de tous les hôpitaux : la période suit le jour local."""
    paris = scene.add_clinic("Nord", "Europe/Paris")
    martinique = scene.add_clinic("Lamentin", "America/Martinique")
    patient, other = scene.add_patient("Léa Martin"), scene.add_patient("Paul Durand")
    late_utc = datetime(2026, 11, 21, 2, tzinfo=UTC)
    in_paris = booked(scene, paris, patient, late_utc)
    in_martinique = booked(scene, martinique, other, late_utc)
    day = date(2026, 11, 20)

    page = scene.queries.page(AdminAppointmentFilter(start_date=day, end_date=day), PageRequest())

    assert [r.appointment.id for r in page.items] == [in_martinique.id]
    assert page.total == 1
    assert in_paris.id not in {
        r.id for r in scene.queries.all(AdminAppointmentFilter(end_date=day))
    }
