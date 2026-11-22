import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.repositories import (
    DjangoAppointments,
    DjangoHolds,
    DjangoWaitlist,
)
from drlibre.interop.application.ports.inbound import (
    AppointmentFilter,
    AppointmentKind,
    InteropAppointmentQueries,
    Paging,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_appointments import SqlInteropAppointmentQueries
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, stored_scene
from tests.builders_organisation import AT
from tests.fakes.clock import FixedClock
from tests.fakes.world import FakeWorld

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
MONDAY = datetime(2026, 11, 23, 8, tzinfo=UTC)
HALF_HOUR = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class Scene:
    """Two clinicians, two patients; their appointments, waitlist entries and holds by name."""

    kind: Id
    room: Id
    first: ClinicianProfile
    second: ClinicianProfile
    anne: Id
    bruno: Id
    ids: dict[str, Id]

    def clinician(self, profile: ClinicianProfile) -> Reader:
        return Reader(ReaderKind.CLINICIAN, profile.user_id, profile.id)

    def patient(self, patient_id: Id) -> Reader:
        return Reader(ReaderKind.PATIENT, patient_id)

    @property
    def admin(self) -> Reader:
        return Reader(ReaderKind.ADMIN, Id())


@dataclass(frozen=True, slots=True)
class Stores:
    appointment: Callable[[Appointment], None]
    entry: Callable[[WaitlistEntry], None]
    hold: Callable[[BookingHold], None]


def _entry(
    scene: Scene,
    status: WaitlistStatus,
    *,
    clinician_id: Id | None = None,
    offered_appointment_id: Id | None = None,
) -> WaitlistEntry:
    return WaitlistEntry(
        id=Id(),
        patient_id=scene.anne,
        appointment_type_id=scene.kind,
        clinician_id=clinician_id,
        earliest=MONDAY + timedelta(days=1),
        latest=MONDAY + timedelta(days=1, hours=8),
        status=status,
        created_at=NOW,
        offered_appointment_id=offered_appointment_id,
    )


def _hold(scene: Scene, start: datetime, expires_at: datetime) -> BookingHold:
    details = VisitorDetails("Ana Martin", date(1990, 5, 17), "ana@example.org", None, "Toux")
    return BookingHold(
        Id(),
        scene.first.id,
        scene.kind,
        start,
        start + HALF_HOUR,
        Source.ONLINE,
        details,
        expires_at,
    )


def _fill(scene: Scene, stores: Stores) -> None:
    """Anne booked with the first clinician, Bruno cancelled with the second, then offered."""
    seen = existing_appointment(
        patient_id=scene.anne,
        clinician_id=scene.first.id,
        appointment_type_id=scene.kind,
        room_id=scene.room,
        start=MONDAY,
        end=MONDAY + HALF_HOUR,
        reason="Douleur",
    )
    seen = dataclasses.replace(seen, clinical_notes="Tension normale")
    later = MONDAY + timedelta(hours=1)
    freed = existing_appointment(
        patient_id=scene.bruno,
        clinician_id=scene.second.id,
        appointment_type_id=scene.kind,
        start=later,
        end=later + HALF_HOUR,
        status=AppointmentStatus.CANCELLED,
    )
    for name, appointment in (("seen", seen), ("freed", freed)):
        stores.appointment(appointment)
        scene.ids[name] = appointment.id
    entries = {
        "waiting": _entry(scene, WaitlistStatus.WAITING, clinician_id=scene.first.id),
        "offered": _entry(scene, WaitlistStatus.OFFERED, offered_appointment_id=freed.id),
        "booked": _entry(scene, WaitlistStatus.BOOKED),
    }
    for name, entry in entries.items():
        stores.entry(entry)
        scene.ids[name] = entry.id
    holds = {
        "held": _hold(scene, MONDAY + timedelta(hours=2), NOW + timedelta(minutes=10)),
        "lapsed": _hold(scene, MONDAY + timedelta(hours=3), NOW - timedelta(minutes=1)),
    }
    for name, hold in holds.items():
        stores.hold(hold)
        scene.ids[name] = hold.id


def _profile(user_id: Id) -> ClinicianProfile:
    fields = {"department_id": str(Id()), "specialty_id": str(Id()), "title": "Dr X"}
    return ClinicianProfile.attach(fields, user_id=user_id, at=AT)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def appointments(request: pytest.FixtureRequest) -> tuple[InteropAppointmentQueries, Scene]:
    if request.param == "fake":
        world = FakeWorld()
        first, second = _profile(Id()), _profile(Id())
        for profile in (first, second):
            world.profiles.save(profile)
        scene = Scene(Id(), Id(), first, second, Id(), Id(), {})
        port = world.app.interop_appointments
        stores = Stores(world.booking_appointments.add, world.waitlist.add, world.holds.add)
    else:
        stored = stored_scene()
        first, second = stored.clinicians
        scene = Scene(stored.kind, stored.room, first, second, Id(), Id(), {})
        port = SqlInteropAppointmentQueries(clock=FixedClock(NOW))
        stores = Stores(DjangoAppointments().add, DjangoWaitlist().add, DjangoHolds().add)
    _fill(scene, stores)
    return port, scene


def names(
    port: InteropAppointmentQueries,
    scene: Scene,
    reader: Reader,
    paging: Paging | None = None,
    **criteria: Any,
) -> list[str]:
    found = port.appointments(
        AppointmentFilter(appointment_type=scene.kind, **criteria),
        reader,
        paging,
    )
    by_id = {i: name for name, i in scene.ids.items()}
    return [by_id[r.id] for r in found.items]


Fixture = tuple[InteropAppointmentQueries, Scene]


def test_a_patient_sees_their_appointments_and_unbooked_entries_by_start(
    appointments: Fixture,
) -> None:
    """Story RDV FHIR: reads are bounded to the patient's appointments; spec §15.3 entries."""
    port, scene = appointments

    assert names(port, scene, scene.patient(scene.anne)) == ["seen", "offered", "waiting"]
    assert names(port, scene, scene.patient(scene.bruno)) == ["freed"]


def test_a_clinician_sees_their_agenda_and_its_open_holds_but_no_waitlist_entry(
    appointments: Fixture,
) -> None:
    """Story RDV FHIR: the clinician's agenda; a hold is `pending` for staff only."""
    port, scene = appointments

    assert names(port, scene, scene.clinician(scene.first)) == ["seen", "held"]
    assert names(port, scene, scene.clinician(scene.second)) == ["freed"]


def test_the_admin_sees_everything_but_booked_entries_and_lapsed_holds(
    appointments: Fixture,
) -> None:
    """Story RDV FHIR: everything for the admin; a booked entry is served as its appointment."""
    port, scene = appointments

    found = names(port, scene, scene.admin)

    assert found[0] == "seen"
    assert sorted(found[1:3]) == ["freed", "offered"]
    assert found[3:] == ["held", "waiting"]
    assert names(port, scene, Reader.anonymous()) == []


def test_clinical_notes_reach_only_the_appointments_clinician(appointments: Fixture) -> None:
    """Story RDV FHIR: `Appointment.comment` only for the appointment's clinician."""
    port, scene = appointments
    seen = AppointmentFilter(ids=(scene.ids["seen"],))

    def notes(reader: Reader) -> str | None:
        return port.appointments(seen, reader).items[0].clinical_notes

    assert notes(scene.clinician(scene.first)) == "Tension normale"
    assert notes(scene.admin) is None
    assert notes(scene.patient(scene.anne)) is None


def test_an_offered_entry_shows_the_offered_slot_and_a_waiting_one_its_window(
    appointments: Fixture,
) -> None:
    """Spec §15.3: `OFFERED` is `proposed` with the offered start, end and practitioner."""
    port, scene = appointments
    rows = {
        r.id: r for r in port.appointments(AppointmentFilter(patient=scene.anne), scene.admin).items
    }
    offered, waiting = rows[scene.ids["offered"]], rows[scene.ids["waiting"]]
    freed = MONDAY + timedelta(hours=1)

    assert (offered.kind, offered.status) == (AppointmentKind.WAITLIST, "OFFERED")
    assert (offered.start, offered.end) == (freed, freed + HALF_HOUR)
    assert (offered.clinician_id, offered.practitioner_id) == (
        scene.second.id,
        scene.second.user_id,
    )
    assert (waiting.start, waiting.earliest) == (None, MONDAY + timedelta(days=1))
    assert waiting.practitioner_id == scene.first.user_id
    held = port.appointments(AppointmentFilter(ids=(scene.ids["held"],)), scene.admin).items[0]
    assert (held.status, held.patient_id, held.reason) == ("HELD", None, "Toux")


def test_searches_narrow_by_patient_practitioner_room_status_and_start(
    appointments: Fixture,
) -> None:
    """Story RDV FHIR: `patient`, `practitioner`, `location`, `status`, `date`, `service-type`."""
    port, scene = appointments
    admin = scene.admin

    assert names(port, scene, admin, patient=scene.bruno) == ["freed"]
    assert names(port, scene, admin, practitioner=scene.first.user_id) == [
        "seen",
        "held",
        "waiting",
    ]
    assert names(port, scene, admin, room=scene.room) == ["seen"]
    cancelled = (("appointment", "CANCELLED"),)
    assert names(port, scene, admin, statuses=cancelled) == ["freed"]
    window = {"start_from": MONDAY + HALF_HOUR, "start_before": MONDAY + timedelta(hours=2)}
    assert sorted(names(port, scene, admin, **window)) == ["freed", "offered"]
    assert port.appointments(AppointmentFilter(appointment_type=Id()), admin).total == 0


def test_a_page_counts_every_match_and_descending_reverses_the_order(
    appointments: Fixture,
) -> None:
    """Story RDV FHIR: searches are paged with their total, `-date` reverses them."""
    port, scene = appointments
    paging = Paging(count=2, page=1, descending=True)

    page = port.appointments(AppointmentFilter(appointment_type=scene.kind), scene.admin, paging)

    assert page.total == 5
    assert names(port, scene, scene.admin, paging) == ["waiting", "held"]


def test_only_served_records_exist(appointments: Fixture) -> None:
    """Story RDV FHIR: a hidden record is forbidden, a booked entry or a lapsed hold absent."""
    port, scene = appointments

    assert port.exists(scene.ids["seen"])
    assert port.exists(scene.ids["waiting"])
    assert port.exists(scene.ids["held"])
    assert not port.exists(scene.ids["booked"])
    assert not port.exists(scene.ids["lapsed"])
    assert not port.exists(Id())
