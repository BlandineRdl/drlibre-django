from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.application.ports.outbound import Appointments, Waitlist
from drlibre.booking.domain.appointment import AppointmentStatus
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments, DjangoWaitlist
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import existing_appointment, stored_scene
from tests.fakes.booking import InMemoryAppointments, InMemoryWaitlist

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
HALF_HOUR = timedelta(minutes=30)


@dataclass
class Scene:
    waitlist: Waitlist
    appointments: Appointments
    kind: Id
    clinician: Id
    other: Id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        appointments = InMemoryAppointments()
        return Scene(InMemoryWaitlist(appointments), appointments, Id(), Id(), Id())
    stored = stored_scene()
    first, second = stored.clinicians
    return Scene(DjangoWaitlist(), DjangoAppointments(), stored.kind, first.id, second.id)


def entry(
    scene: Scene,
    *,
    patient: Id | None = None,
    clinician: Id | None = None,
    days: int = 7,
    joined: datetime = NOW,
) -> WaitlistEntry:
    made = WaitlistEntry.join(
        patient_id=patient or Id(),
        appointment_type_id=scene.kind,
        clinician_id=clinician,
        earliest=NOW,
        latest=NOW + timedelta(days=days),
        at=joined,
    )
    scene.waitlist.add(made)
    return made


def freed(scene: Scene, start: datetime) -> Id:
    appointment = existing_appointment(
        patient_id=Id(),
        clinician_id=scene.clinician,
        appointment_type_id=scene.kind,
        start=start,
        end=start + HALF_HOUR,
        status=AppointmentStatus.CANCELLED,
    )
    scene.appointments.add(appointment)
    return appointment.id


def test_an_entry_is_stored_and_read_back_whatever_its_status(scene: Scene) -> None:
    """Règle §3.1 : une entrée garde son patient, son type, son praticien et sa fenêtre."""
    stored = entry(scene, clinician=scene.clinician)
    offered = stored.offered(freed(scene, NOW + timedelta(days=1)))

    scene.waitlist.save(offered)

    assert scene.waitlist.get(stored.id) == offered
    assert scene.waitlist.get_locked(stored.id) == offered
    assert scene.waitlist.get(Id()) is None
    assert scene.waitlist.get_locked(Id()) is None


def test_saving_an_unknown_entry_is_refused_as_not_found(scene: Scene) -> None:
    unknown = WaitlistEntry.join(
        patient_id=Id(),
        appointment_type_id=scene.kind,
        clinician_id=None,
        earliest=NOW,
        latest=NOW + timedelta(days=1),
        at=NOW,
    )
    with pytest.raises(DomainError) as refused:
        scene.waitlist.save(unknown)
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_a_freed_slot_matches_waiting_entries_of_its_type_window_and_clinician(
    scene: Scene,
) -> None:
    """Règle §5.8 : même type, praticien préféré vide ou égal, créneau dans la fenêtre."""
    cancelling = Id()
    anyone = entry(scene)
    preferred = entry(scene, clinician=scene.clinician)
    entry(scene, clinician=scene.other)
    entry(scene, days=1)
    entry(scene, patient=cancelling)
    offered = entry(scene)
    scene.waitlist.save(offered.offered(freed(scene, NOW + timedelta(days=3))))
    start = NOW + timedelta(days=2)

    found = scene.waitlist.candidates_locked(
        appointment_type_id=scene.kind,
        clinician_id=scene.clinician,
        start=start,
        end=start + HALF_HOUR,
        excluding_patient=cancelling,
    )

    assert [e.id for e in found] == sorted([anyone.id, preferred.id], key=lambda i: i.value)


def test_an_appointment_is_held_only_while_an_entry_is_offered_it(scene: Scene) -> None:
    appointment = freed(scene, NOW + timedelta(days=1))
    offered = entry(scene).offered(appointment)
    scene.waitlist.save(offered)

    assert scene.waitlist.holds_offer(appointment)
    scene.waitlist.save(offered.back_to_waiting())
    assert not scene.waitlist.holds_offer(appointment)


def test_a_second_open_offer_of_one_appointment_is_a_conflict(scene: Scene) -> None:
    """Décision du plan : un RDV libéré n'est proposé qu'à une entrée à la fois."""
    appointment = freed(scene, NOW + timedelta(days=1))
    scene.waitlist.save(entry(scene).offered(appointment))
    second = entry(scene)

    with pytest.raises(DomainError) as refused:
        scene.waitlist.save(second.offered(appointment))

    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.details == {"resources": ["waitlist_entry"]}
    assert scene.waitlist.get(second.id) == second


def test_entries_past_their_window_or_offer_start_are_due_for_expiry(scene: Scene) -> None:
    """Décision du plan : le job expire les attentes échues et libère les offres commencées."""
    later = NOW + timedelta(days=2)
    past_window = entry(scene, days=1)
    started_at = NOW + timedelta(days=1)
    started = entry(scene)
    scene.waitlist.save(started.offered(freed(scene, started_at)))
    entry(scene)
    future = entry(scene)
    scene.waitlist.save(future.offered(freed(scene, NOW + timedelta(days=3))))
    booked = entry(scene, days=1)
    scene.waitlist.save(booked.offered(freed(scene, NOW + HALF_HOUR)).booked())

    due = scene.waitlist.expiring_locked(later)

    expected = sorted(
        [(past_window.id, None), (started.id, started_at)], key=lambda pair: pair[0].value
    )
    assert [(d.entry.id, d.offered_start) for d in due] == expected
    assert due[0].entry == scene.waitlist.get(due[0].entry.id)
    assert all(d.entry.status is not WaitlistStatus.BOOKED for d in due)
