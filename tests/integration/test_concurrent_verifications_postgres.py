import dataclasses
from datetime import datetime, timedelta

import pytest

from drlibre.booking.domain.booking_rules import MAX_OPEN_ONLINE
from drlibre.booking.domain.verification_code import MAX_ATTEMPTS, VerificationCode
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import (
    DjangoAppointments,
    DjangoHolds,
    DjangoVerificationCodes,
)
from drlibre.bootstrap.container import wire
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


class RacingAppointments(DjangoAppointments):
    def __init__(self, race: Race) -> None:
        self._race = race

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        # Read before booking, so without the patient lock both verifications count the same two.
        found = super().open_online_count(patient_id, now)
        self._race.hold_first()
        return found


def hold_for(world: Bookable, email: str, clinician: Id, start: datetime) -> tuple[Id, str]:
    visitor = {**world.visitor(), "email": email}
    created = world.app().create_hold.execute(
        appointment_type_id=world.scene.kind,
        clinician_id=clinician,
        start=start,
        **visitor,  # type: ignore[arg-type]
    )
    return created.hold_id, world.code()


def test_two_verifications_of_one_patient_at_once_never_exceed_three_open_bookings() -> None:
    """Story réservation : au plus 3 réservations ouvertes, même validées en même temps."""
    race = Race()
    with bookable() as world:
        first_clinician, second_clinician = (profile.id for profile in world.scene.clinicians)
        patient = stored_user(Role.PATIENT, password=None)
        for offset in range(MAX_OPEN_ONLINE - 1):
            world.app().book_appointment.execute(
                patient_id=patient.id,
                appointment_type_id=world.scene.kind,
                clinician_id=first_clinician,
                start=SLOT_START + timedelta(minutes=30 * offset),
            )
        email = patient.email.value
        later = SLOT_START + timedelta(hours=1)
        first_hold, first_code = hold_for(world, email, first_clinician, later)
        kept_hold = DjangoHolds().get(first_hold)
        kept_code = DjangoVerificationCodes().for_hold(first_hold)
        second_hold, second_code = hold_for(
            world, email, second_clinician, later + timedelta(minutes=30)
        )
        # A second hold of one email replaces the first: put it back to race two verifications.
        assert kept_hold is not None
        assert kept_code is not None
        DjangoHolds().add(kept_hold)
        DjangoVerificationCodes().put(kept_code)
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, appointments=RacingAppointments(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def verify(hold_id: Id, code: str):
            def run() -> object:
                done = app.verify_hold.execute(hold_id=hold_id, code=code, user_agent="test")
                if isinstance(done.outcome, DomainError):
                    raise done.outcome
                return done

            return run

        outcomes = race.run(verify(first_hold, first_code), verify(second_hold, second_code))

        assert race.second_was_blocked == [True]
        assert outcomes == ["rule_violation", "saved"]
        assert AppointmentRecord.objects.filter(patient_id=patient.id.value).count() == (
            MAX_OPEN_ONLINE
        )


class RacingCodes(DjangoVerificationCodes):
    def __init__(self, race: Race) -> None:
        self._race = race

    def for_hold_locked(self, hold_id: Id) -> VerificationCode | None:
        # Read before counting the failure, so without the code lock both lose one increment.
        found = super().for_hold_locked(hold_id)
        self._race.hold_first()
        return found


def test_two_wrong_codes_at_once_both_count_as_attempts() -> None:
    """Story réservation : 5 essais de code au plus, même saisis en même temps."""
    race = Race()
    with bookable() as world:
        hold_id, _ = hold_for(world, "visitor@example.org", world.clinician, SLOT_START)
        stored = DjangoVerificationCodes().for_hold(hold_id)
        assert stored is not None
        DjangoVerificationCodes().put(dataclasses.replace(stored, attempts=MAX_ATTEMPTS - 2))
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, codes=RacingCodes(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def verify() -> object:
            return app.verify_hold.execute(hold_id=hold_id, code="000000", user_agent="test")

        outcomes = race.run(verify, verify)

        after = DjangoVerificationCodes().for_hold(hold_id)
        assert race.second_was_blocked == [True]
        assert outcomes == ["invalid_input", "invalid_input"]
        assert after is not None
        assert after.attempts == MAX_ATTEMPTS


def test_two_correct_codes_at_once_open_one_booking_and_refuse_the_other() -> None:
    """Story réservation : un code correct ne sert qu'une fois, même saisi en même temps."""
    race = Race()
    with bookable() as world:
        hold_id, code = hold_for(world, "visitor@example.org", world.clinician, SLOT_START)
        adapters = world.at(NOW)
        racing = dataclasses.replace(adapters.booking, codes=RacingCodes(race))
        app = wire(dataclasses.replace(adapters, booking=racing))

        def verify() -> object:
            done = app.verify_hold.execute(hold_id=hold_id, code=code, user_agent="test")
            if isinstance(done.outcome, DomainError):
                raise done.outcome
            return done

        outcomes = race.run(verify, verify)

        assert race.second_was_blocked == [True]
        assert outcomes == ["invalid_input", "saved"]
        assert AppointmentRecord.objects.filter(clinician_id=world.clinician.value).count() == 1
