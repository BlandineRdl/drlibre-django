from datetime import timedelta

import pytest

from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.search.application.ports.inbound import SearchCriteria
from drlibre.shared_kernel.booking_policy import BOOKING_LEAD_TIME
from drlibre.shared_kernel.errors import DomainError
from tests.integration.bookable import NOW, SLOT_START, bookable

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

WINDOW = timedelta(days=31)


def test_the_slots_search_shows_are_those_booking_would_accept() -> None:
    """Story créneaux : les créneaux montrés sont exactement ceux que la réservation accepterait."""
    with bookable() as world:
        app = world.app()
        held, other = world.scene.clinicians
        app.create_hold.execute(
            appointment_type_id=world.scene.kind,
            clinician_id=held.id,
            start=SLOT_START,
            **world.visitor(),  # type: ignore[arg-type]
        )
        start = NOW + BOOKING_LEAD_TIME

        def accepted(clinician: object | None) -> list:
            return [
                s.start
                for s in app.find_free_slots.execute(
                    appointment_type_id=world.scene.kind,
                    clinician_id=clinician,  # type: ignore[arg-type]
                    start=start,
                    end=start + WINDOW,
                )
            ]

        shown = {p.id: p for p in app.search_providers.execute(SearchCriteria()).items}
        for profile in (held, other):
            expected = accepted(profile.id)[:3]
            next_slots = shown[profile.id].next_slots
            assert next_slots is not None
            assert list(next_slots.starts) == expected
        assert SLOT_START not in shown[held.id].next_slots.starts  # type: ignore[union-attr]
        assert SLOT_START in shown[other.id].next_slots.starts  # type: ignore[union-attr]

        hospital = app.search_hospitals.execute(SearchCriteria()).items[0]
        assert hospital.first_slot is not None
        assert hospital.first_slot.start == accepted(None)[0]
        assert hospital.providers_with_slots == 2

        week = app.view_provider_page.execute(
            provider_id=held.id, type_id=world.scene.kind, week=SLOT_START.date()
        )
        assert list(week.starts) == [s for s in accepted(held.id) if s.date() == SLOT_START.date()]


def test_an_inactive_clinician_shows_no_slot_in_search_and_none_in_booking() -> None:
    """Story créneaux : un praticien inactif n'a plus de créneau, ni affiché ni réservable."""
    with bookable() as world:
        app = world.app()
        inactive, active = world.scene.clinicians
        UserRecord.objects.filter(pk=inactive.user_id.value).update(active=False)
        start = NOW + BOOKING_LEAD_TIME

        shown = {p.id for p in app.search_providers.execute(SearchCriteria()).items}
        hospital = app.search_hospitals.execute(SearchCriteria()).items[0]
        accepted = [
            s.start
            for s in app.find_free_slots.execute(
                appointment_type_id=world.scene.kind,
                clinician_id=None,
                start=start,
                end=start + WINDOW,
            )
        ]

        assert inactive.id not in shown
        assert active.id in shown
        assert hospital.providers_with_slots == 1
        assert hospital.first_slot is not None
        assert hospital.first_slot.start == accepted[0]
        with pytest.raises(DomainError):
            app.find_free_slots.execute(
                appointment_type_id=world.scene.kind,
                clinician_id=inactive.id,
                start=start,
                end=start + WINDOW,
            )
