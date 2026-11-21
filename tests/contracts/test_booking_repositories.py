from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.application.ports.outbound import Appointments, Holds, VerificationCodes
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.infrastructure.repositories import (
    DjangoAppointments,
    DjangoHolds,
    DjangoVerificationCodes,
)
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import stored_scene
from tests.fakes.booking import InMemoryAppointments, InMemoryHolds, InMemoryVerificationCodes

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


def at(hours: int) -> datetime:
    return NOW + timedelta(hours=hours)


@dataclass
class Scene:
    appointments: Appointments
    holds: Holds
    codes: VerificationCodes
    clinician: Id
    other: Id
    kind: Id
    room: Id


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> Scene:
    if request.param == "fake":
        return Scene(
            InMemoryAppointments(),
            InMemoryHolds(),
            InMemoryVerificationCodes(),
            Id(),
            Id(),
            Id(),
            Id(),
        )
    stored = stored_scene()
    return Scene(
        DjangoAppointments(),
        DjangoHolds(),
        DjangoVerificationCodes(),
        stored.clinicians[0].id,
        stored.clinicians[1].id,
        stored.kind,
        stored.room,
    )


def appointment(
    scene: Scene,
    *,
    patient: Id,
    start: datetime,
    hours: int = 1,
    clinician: Id | None = None,
    room: Id | None = None,
    source: Source = Source.ONLINE,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Appointment:
    return Appointment(
        id=Id(),
        patient_id=patient,
        clinician_id=clinician or scene.clinician,
        appointment_type_id=scene.kind,
        room_id=room,
        start=start,
        end=start + timedelta(hours=hours),
        status=status,
        source=source,
        reason="Douleur",
    )


def hold(scene: Scene, *, start: datetime, email: str = "visiteur@example.org", at: datetime = NOW):
    details = VisitorDetails(
        full_name="Ana Martin",
        birth_date=date(1990, 5, 17),
        email=email,
        phone=None,
        reason=None,
    )
    return BookingHold.open(
        clinician_id=scene.clinician,
        appointment_type_id=scene.kind,
        start=start,
        duration=timedelta(minutes=30),
        source=Source.ROUND_ROBIN,
        details=details,
        at=at,
    )


def test_an_appointment_conflicts_on_the_clinician_and_on_the_patient_while_active(
    scene: Scene,
) -> None:
    """Story réservation : un créneau déjà occupé est refusé avec le conflit."""
    patient = Id()
    scene.appointments.add(appointment(scene, patient=patient, start=at(5)))
    cancelled = AppointmentStatus.CANCELLED
    scene.appointments.add(appointment(scene, patient=Id(), start=at(8), status=cancelled))

    def conflicts(who: Id, clinician: Id, start: datetime) -> tuple[str, ...]:
        return scene.appointments.conflicting_resources(
            clinician_id=clinician, patient_id=who, start=start, end=start + timedelta(hours=1)
        )

    assert conflicts(patient, scene.other, at(5)) == ("patient",)
    assert conflicts(Id(), scene.clinician, at(5)) == ("clinician",)
    assert conflicts(patient, scene.clinician, at(5)) == ("clinician", "patient")
    assert conflicts(patient, scene.clinician, at(6)) == ()
    assert conflicts(Id(), scene.clinician, at(8)) == ()
    assert scene.appointments.clinician_busy(scene.clinician, at(5), at(6))
    assert not scene.appointments.clinician_busy(scene.clinician, at(8), at(9))
    assert not scene.appointments.clinician_busy(scene.other, at(5), at(6))


def test_a_stored_appointment_is_read_back_whatever_its_status(scene: Scene) -> None:
    """Story confirmation : la page de confirmation relit le rendez-vous enregistré."""
    cancelled = appointment(
        scene, patient=Id(), start=at(5), status=AppointmentStatus.CANCELLED, room=scene.room
    )
    scene.appointments.add(cancelled)

    assert scene.appointments.get(cancelled.id) == cancelled
    assert scene.appointments.get(Id()) is None


def test_only_future_active_online_appointments_count_as_open_bookings(scene: Scene) -> None:
    """Story réservation : trois réservations en ligne ouvertes au plus par patient."""
    patient = Id()
    make = appointment
    for start, source, status in (
        (at(3), Source.ONLINE, AppointmentStatus.BOOKED),
        (at(4), Source.ROUND_ROBIN, AppointmentStatus.CONFIRMED),
        (at(5), Source.STAFF, AppointmentStatus.BOOKED),
        (at(6), Source.ONLINE, AppointmentStatus.CANCELLED),
        (at(7), Source.ONLINE, AppointmentStatus.NO_SHOW),
        (at(-5), Source.ONLINE, AppointmentStatus.COMPLETED),
    ):
        scene.appointments.add(
            make(scene, patient=patient, start=start, source=source, status=status)
        )
    scene.appointments.add(appointment(scene, patient=Id(), start=at(9)))

    assert scene.appointments.open_online_count(patient, NOW) == 2
    assert scene.appointments.open_online_count(Id(), NOW) == 0


def test_a_room_is_busy_only_while_an_active_appointment_overlaps(scene: Scene) -> None:
    """Story réservation : une salle occupée n'est pas attribuée."""
    scene.appointments.add(appointment(scene, patient=Id(), start=at(5), room=scene.room))
    cancelled = AppointmentStatus.CANCELLED
    scene.appointments.add(
        appointment(scene, patient=Id(), start=at(8), room=scene.room, status=cancelled)
    )

    assert scene.appointments.busy_rooms((scene.room,), at(5), at(6)) == {scene.room}
    assert scene.appointments.busy_rooms((scene.room,), at(6), at(7)) == frozenset()
    assert scene.appointments.busy_rooms((scene.room,), at(8), at(9)) == frozenset()
    assert scene.appointments.busy_rooms((), at(5), at(6)) == frozenset()


def test_a_hold_keeps_its_details_and_is_open_until_its_expiry(scene: Scene) -> None:
    """Story réservation provisoire : le créneau est gardé 10 minutes."""
    held = hold(scene, start=at(5))
    scene.holds.add(held)

    assert scene.holds.get(held.id) == held
    assert scene.holds.open_for_email(held.email, NOW + timedelta(minutes=9)) == held
    assert scene.holds.open_for_email(held.email, held.expires_at) is None
    assert scene.holds.open_for_email("autre@example.org", NOW) is None


def test_an_expired_hold_frees_the_slot_without_any_job(scene: Scene) -> None:
    """Décision du plan : l'expiration est lue à la lecture, jamais laissée à un job."""
    held = hold(scene, start=at(5))
    scene.holds.add(held)
    inside = (held.start, held.end)

    def is_held(when: datetime, excluding: Id | None = None) -> bool:
        return scene.holds.held(scene.clinician, *inside, at=when, excluding=excluding)

    assert is_held(NOW)
    assert not is_held(NOW, excluding=held.id)
    assert not is_held(held.expires_at)
    assert not scene.holds.held(scene.other, *inside, at=NOW, excluding=None)
    assert not scene.holds.held(
        scene.clinician, held.end, held.end + timedelta(hours=1), at=NOW, excluding=None
    )
    assert scene.holds.open_in((scene.clinician,), *inside, at=NOW) == (held,)
    assert scene.holds.open_in((scene.clinician,), *inside, at=held.expires_at) == ()
    assert scene.holds.open_in((scene.other,), *inside, at=NOW) == ()


def test_expired_holds_are_listed_then_deleted(scene: Scene) -> None:
    """Story réservation provisoire : une réservation expirée est supprimée."""
    old = hold(scene, start=at(5), email="ancien@example.org")
    fresh = hold(scene, start=at(7), email="frais@example.org", at=NOW + timedelta(hours=1))
    scene.holds.add(old)
    scene.holds.add(fresh)

    assert scene.holds.expired(NOW + timedelta(minutes=30)) == (old,)

    scene.holds.delete(old.id)
    scene.holds.delete(old.id)

    assert scene.holds.get(old.id) is None
    assert scene.holds.expired(NOW + timedelta(minutes=30)) == ()


def test_a_code_is_replaced_per_hold_and_removed_with_it(scene: Scene) -> None:
    """Story code : un renvoi annule le code précédent."""
    held = hold(scene, start=at(5))
    scene.holds.add(held)
    first = VerificationCode.issue(hold_id=held.id, email=held.email, code_hash="a" * 64, at=NOW)
    scene.codes.put(first)
    assert scene.codes.for_hold(held.id) == first

    failed = first.failed_once()
    scene.codes.put(failed)
    assert scene.codes.for_hold(held.id) == failed
    assert scene.codes.for_hold_locked(held.id) == failed

    second = VerificationCode.issue(hold_id=held.id, email=held.email, code_hash="b" * 64, at=NOW)
    scene.codes.put(second)
    assert scene.codes.for_hold(held.id) == second

    scene.codes.delete_for_hold(held.id)
    scene.codes.delete_for_hold(held.id)
    assert scene.codes.for_hold(held.id) is None
    assert scene.codes.for_hold_locked(held.id) is None
