from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from pytest_django import DjangoAssertNumQueries

from drlibre.booking.application.ports.outbound import AgendaEntry, AgendaFilter, PatientAgenda
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.patient_agenda import SqlPatientAgenda
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, stored_scene
from tests.fakes.booking import AgendaClinician, InMemoryAppointments, InMemoryPatientAgenda

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
# What the stored scene names, as the SQL join reads it back.
CLINICIAN = AgendaClinician(
    name="Demo Clinician",
    title="Dr X",
    specialty="Cardiologie",
    hospital_name="Hôpital Nord",
    hospital_address="1 rue de la Paix, 59000 Lille",
    time_zone="Europe/Paris",
    department="Cardiologie",
)


@dataclass
class Scene:
    agenda: PatientAgenda
    add: Callable[[Appointment], None]
    clinicians: tuple[Id, Id]
    kind: Id
    room: Id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        appointments = InMemoryAppointments()
        agenda = InMemoryPatientAgenda(appointments)
        clinicians, kind, room = (Id(), Id()), Id(), Id()
        agenda.clinicians.update(dict.fromkeys(clinicians, CLINICIAN))
        agenda.labels.update({kind: "Consultation", room: "Salle 1"})
        return Scene(agenda, appointments.add, clinicians, kind, room)
    stored = stored_scene()
    clinicians = (stored.clinicians[0].id, stored.clinicians[1].id)
    return Scene(SqlPatientAgenda(), DjangoAppointments().add, clinicians, stored.kind, stored.room)


def stored_appointment(
    scene: Scene,
    patient: Id,
    hours: int,
    *,
    second: bool = False,
    room: bool = True,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Appointment:
    start = NOW + timedelta(hours=hours)
    appointment = existing_appointment(
        patient_id=patient,
        clinician_id=scene.clinicians[1 if second else 0],
        appointment_type_id=scene.kind,
        start=start,
        end=start + timedelta(minutes=30),
        room_id=scene.room if room else None,
        status=status,
        reason="Douleur",
    )
    scene.add(appointment)
    return appointment


def starts(entries: tuple[AgendaEntry, ...]) -> list[datetime]:
    return [entry.appointment.start for entry in entries]


def test_the_agenda_lists_only_the_patients_appointments_by_start_with_whom_and_where(
    scene: Scene,
) -> None:
    """Story « retrouve ses RDV » : praticien, hôpital, département, salle, type et motif."""
    patient = Id()
    later = stored_appointment(scene, patient, 48)
    sooner = stored_appointment(scene, patient, 24, second=True, room=False)
    stored_appointment(scene, Id(), 30)

    entries = scene.agenda.entries(patient, AgendaFilter())

    fields = (
        CLINICIAN.name,
        CLINICIAN.title,
        CLINICIAN.specialty,
        CLINICIAN.hospital_name,
        CLINICIAN.hospital_address,
        CLINICIAN.time_zone,
        CLINICIAN.department,
    )
    assert entries == (
        AgendaEntry(sooner, *fields, room=None, appointment_type="Consultation"),
        AgendaEntry(later, *fields, room="Salle 1", appointment_type="Consultation"),
    )


def test_the_agenda_narrows_to_a_clinician_a_status_and_a_start_range(scene: Scene) -> None:
    """Story « retrouve ses RDV » : GET /appointments filtre par praticien, statut et période."""
    patient = Id()
    stored_appointment(scene, patient, 24)
    stored_appointment(scene, patient, 30, second=True)
    stored_appointment(scene, patient, 48, status=AppointmentStatus.CANCELLED)
    stored_appointment(scene, patient, 72)
    hours = [NOW + timedelta(hours=h) for h in (24, 30, 48, 72)]

    by_clinician = AgendaFilter(clinician_id=scene.clinicians[1])
    by_status = AgendaFilter(status=AppointmentStatus.CANCELLED)
    by_range = AgendaFilter(start=hours[1], end=hours[3])

    assert starts(scene.agenda.entries(patient, by_clinician)) == [hours[1]]
    assert starts(scene.agenda.entries(patient, by_status)) == [hours[2]]
    assert starts(scene.agenda.entries(patient, by_range)) == hours[1:3]


@pytest.mark.integration
@pytest.mark.django_db
def test_a_patients_agenda_page_costs_one_sql_query(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """Plan E4 : une seule requête par page d'agenda, quel que soit le nombre de RDV."""
    stored = stored_scene()
    scene = Scene(
        SqlPatientAgenda(),
        DjangoAppointments().add,
        (stored.clinicians[0].id, stored.clinicians[1].id),
        stored.kind,
        stored.room,
    )
    patient = Id()
    for hours in (24, 30, 48):
        stored_appointment(scene, patient, hours)

    with django_assert_num_queries(1):
        entries = scene.agenda.entries(patient, AgendaFilter())

    assert len(entries) == 3
