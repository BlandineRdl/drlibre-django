import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest
from pytest_django import DjangoAssertNumQueries

from drlibre.booking.application.ports.outbound import (
    ClinicianAgenda,
    ClinicianFilter,
    RoomBooking,
    RoomLabel,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.infrastructure.clinician_agenda import SqlClinicianAgenda
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoHolds
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.scheduling.application.ports.outbound import StoredSlot
from drlibre.scheduling.domain.slot import Slot
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PageRequest
from tests.builders import unique_email
from tests.builders_booking import (
    bookable_clinician,
    existing_appointment,
    patient_user,
    stored_scene,
)
from tests.fakes.booking import FixedBookingDirectory, InMemoryAppointments, InMemoryHolds
from tests.fakes.clinician_agenda import InMemoryClinicianAgenda
from tests.fakes.scheduling import InMemorySlotStore
from tests.fakes.users import InMemoryUsers

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
BIRTH = date(1980, 1, 1)


def stored_slots(clinician: Id, kind: Id, starts: tuple[datetime, ...]) -> tuple[StoredSlot, ...]:
    return tuple(StoredSlot(clinician, kind, Slot(s, s + timedelta(minutes=30))) for s in starts)


@dataclass
class Scene:
    agenda: ClinicianAgenda
    add: Callable[[Appointment], None]
    save_user: Callable[..., None]
    add_slots: Callable[[Id, tuple[datetime, ...]], None]
    add_hold: Callable[[BookingHold], None]
    clinicians: tuple[Id, Id]
    kind: Id
    room: Id

    def patient(self, name: str) -> Id:
        patient_id = Id()
        user = patient_user(patient_id, email=unique_email("patient"))
        self.save_user(dataclasses.replace(user, full_name=name))
        return patient_id


def fake_scene() -> Scene:
    appointments, users, holds = InMemoryAppointments(), InMemoryUsers(), InMemoryHolds()
    directory, slots = FixedBookingDirectory(), InMemorySlotStore()
    agenda = InMemoryClinicianAgenda(
        appointments=appointments, users=users, directory=directory, slots=slots, holds=holds
    )
    department, kind, room = Id(), Id(), Id()
    clinicians = bookable_clinician(department), bookable_clinician(department)
    for clinician in clinicians:
        directory.clinicians[clinician.id] = clinician
    directory.department_rooms[department] = (room,)
    agenda.labels.update({kind: "Consultation", room: "Salle 1"})
    agenda.colours[kind] = "#336699"

    def add_slots(clinician: Id, starts: tuple[datetime, ...]) -> None:
        slots.rows.extend(stored_slots(clinician, kind, starts))

    return Scene(
        agenda,
        appointments.add,
        users.save,
        add_slots,
        holds.add,
        (clinicians[0].id, clinicians[1].id),
        kind,
        room,
    )


def real_scene() -> Scene:
    stored = stored_scene()
    kind = stored.kind

    def add_slots(clinician: Id, starts: tuple[datetime, ...]) -> None:
        DjangoSlotStore().replace(clinician, stored_slots(clinician, kind, starts))

    return Scene(
        SqlClinicianAgenda(),
        DjangoAppointments().add,
        DjangoUsers().save,
        add_slots,
        DjangoHolds().add,
        (stored.clinicians[0].id, stored.clinicians[1].id),
        kind,
        stored.room,
    )


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    return fake_scene() if request.param == "fake" else real_scene()


def stored(
    scene: Scene,
    patient: Id,
    hours: float,
    *,
    second: bool = False,
    room: bool = True,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
    notes: str | None = None,
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
    appointment = dataclasses.replace(appointment, clinical_notes=notes)
    scene.add(appointment)
    return appointment


def test_the_agenda_lists_only_the_clinicians_appointments_with_patient_type_and_room(
    scene: Scene,
) -> None:
    """Story « agenda du jour » : patient, type, salle et statut, les siens seuls."""
    marie, paul = scene.patient("Marie Curie"), scene.patient("Paul Valéry")
    later = stored(scene, marie, 4, notes="Suivi")
    sooner = stored(scene, paul, 2, room=False, status=AppointmentStatus.CANCELLED)
    stored(scene, marie, 3, second=True)

    entries = scene.agenda.entries(scene.clinicians[0], ClinicianFilter())

    assert [e.appointment.id for e in entries] == [sooner.id, later.id]
    first, second = entries
    assert (first.patient_name, first.room, first.appointment.status) == (
        "Paul Valéry",
        None,
        AppointmentStatus.CANCELLED,
    )
    assert (
        second.patient_name,
        second.patient_phone,
        second.patient_birth_date,
        second.appointment_type,
        second.type_colour,
        second.room,
        second.appointment.clinical_notes,
        second.actions,
    ) == (
        "Marie Curie",
        "0600000000",
        BIRTH,
        "Consultation",
        "#336699",
        "Salle 1",
        None,
        frozenset(),
    )


def test_the_agenda_narrows_to_a_patient_a_status_and_a_start_range(scene: Scene) -> None:
    """Story « agenda du jour » : GET /appointments filtre par patient, statut et période."""
    marie, paul = scene.patient("Marie Curie"), scene.patient("Paul Valéry")
    stored(scene, marie, 1)
    stored(scene, paul, 2)
    stored(scene, marie, 3, status=AppointmentStatus.COMPLETED)
    hours = [NOW + timedelta(hours=h) for h in (1, 2, 3)]

    def starts(f: ClinicianFilter) -> list[datetime]:
        return [e.appointment.start for e in scene.agenda.entries(scene.clinicians[0], f)]

    assert starts(ClinicianFilter(patient_id=marie)) == [hours[0], hours[2]]
    assert starts(ClinicianFilter(status=AppointmentStatus.COMPLETED)) == [hours[2]]
    assert starts(ClinicianFilter(start=hours[1], end=hours[2])) == [hours[1]]


def test_the_detail_of_an_appointment_carries_its_clinical_notes(scene: Scene) -> None:
    """Story « notes cliniques » : la fiche montre au praticien les notes enregistrées."""
    noted = stored(scene, scene.patient("Marie Curie"), 2, notes="Tension normale")

    found = scene.agenda.detail(noted.id)

    assert found is not None
    assert (found.appointment, found.patient_name) == (noted, "Marie Curie")
    assert scene.agenda.detail(Id()) is None


def test_the_patients_are_those_seen_by_the_clinician_with_last_and_next_visit(
    scene: Scene,
) -> None:
    """Story « retrouve ses patients » : téléphone, dernière et prochaine visite, eux seuls."""
    marie, marc = scene.patient("Marie Curie"), scene.patient("Marc Bloch")
    stranger = scene.patient("Martin Nadaud")
    stored(scene, marie, -48, status=AppointmentStatus.COMPLETED)
    stored(scene, marie, -24, status=AppointmentStatus.COMPLETED)
    stored(scene, marie, -2, status=AppointmentStatus.NO_SHOW)
    stored(scene, marie, 24, status=AppointmentStatus.CANCELLED)
    stored(scene, marie, 48)
    stored(scene, marie, 72)
    stored(scene, marc, 5, status=AppointmentStatus.CHECKED_IN)
    stored(scene, stranger, 6, second=True)

    page = scene.agenda.patients(scene.clinicians[0], PageRequest(), NOW)

    assert page.total == 2
    assert [
        (p.patient_id, p.full_name, p.phone, p.last_visit, p.next_visit) for p in page.items
    ] == [
        (marc, "Marc Bloch", "0600000000", None, NOW + timedelta(hours=5)),
        (marie, "Marie Curie", "0600000000", NOW - timedelta(hours=24), NOW + timedelta(hours=48)),
    ]


def test_a_search_by_name_filters_the_patients(scene: Scene) -> None:
    """Story « retrouve ses patients » : une recherche par nom filtre la liste."""
    marie, paul = scene.patient("Marie Curie"), scene.patient("Paul Valéry")
    stored(scene, marie, 2)
    stored(scene, paul, 3)

    found = scene.agenda.patients(scene.clinicians[0], PageRequest(search="MAR"), NOW)
    wildcard = scene.agenda.patients(scene.clinicians[0], PageRequest(search="%"), NOW)

    assert [p.patient_id for p in found.items] == [marie]
    assert wildcard.items == ()


def test_the_rooms_day_names_only_the_clinicians_own_patients(scene: Scene) -> None:
    """Story « occupation des salles » : ses RDV nomment le patient, les autres non."""
    marie, paul = scene.patient("Marie Curie"), scene.patient("Paul Valéry")
    mine = stored(scene, marie, 1)
    theirs = stored(scene, paul, 2, second=True)
    stored(scene, paul, 3, status=AppointmentStatus.CANCELLED)
    stored(scene, marie, 4, room=False)
    stored(scene, marie, 30)

    day = scene.agenda.room_day(scene.clinicians[0], NOW, NOW + timedelta(hours=24))

    assert day.rooms == (RoomLabel(scene.room, "Salle 1"),)
    assert day.bookings == (
        RoomBooking(scene.room, mine.start, mine.end, "Marie Curie"),
        RoomBooking(scene.room, theirs.start, theirs.end, None),
    )


def test_the_next_free_slot_skips_a_held_slot(scene: Scene) -> None:
    """Story « agenda du jour » : le prochain créneau libre n'est pas tenu par une réservation."""
    clinician = scene.clinicians[0]
    held, free = NOW + timedelta(hours=1), NOW + timedelta(hours=2)
    scene.add_slots(clinician, (held, free))
    details = VisitorDetails(
        full_name="Ana Martin", birth_date=BIRTH, email="ana@example.org", phone=None, reason=None
    )
    scene.add_hold(
        BookingHold.open(
            clinician_id=clinician,
            appointment_type_id=scene.kind,
            start=held,
            duration=timedelta(minutes=30),
            source=Source.ONLINE,
            details=details,
            at=NOW,
        )
    )

    assert scene.agenda.next_free_slot(clinician, NOW, NOW) == free
    assert scene.agenda.next_free_slot(clinician, free + timedelta(minutes=1), NOW) is None


@pytest.mark.integration
@pytest.mark.django_db
def test_a_clinicians_day_costs_one_sql_query(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """Plan E6 : une seule requête par liste de l'agenda, quel que soit le nombre de RDV."""
    scene = real_scene()
    patient = scene.patient("Marie Curie")
    for hours in (1, 2, 3):
        stored(scene, patient, hours)

    with django_assert_num_queries(1):
        entries = scene.agenda.entries(scene.clinicians[0], ClinicianFilter())

    assert len(entries) == 3
