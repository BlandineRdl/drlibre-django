from datetime import datetime, timedelta

import pytest

from drlibre.bootstrap.container import Container
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import AppointmentTypeRecord
from drlibre.search.application.ports.inbound import SearchCriteria
from drlibre.shared_kernel.booking_policy import BOOKING_LEAD_TIME
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable

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


def test_a_slot_whose_department_rooms_are_all_taken_is_neither_shown_nor_booked() -> None:
    """Règle §6.2 : un créneau aux salles du département toutes prises n'est pas proposé."""
    with bookable() as world:
        AppointmentTypeRecord.objects.filter(pk=world.scene.kind.value).update(needs_room=True)
        app = world.app()
        free, other = world.scene.clinicians
        taken = book(app, world, other.id, SLOT_START)
        start = NOW + BOOKING_LEAD_TIME

        def accepted(clinician: Id, ignoring: Id | None = None) -> list:
            return [
                s.start
                for s in app.find_free_slots.execute(
                    appointment_type_id=world.scene.kind,
                    clinician_id=clinician,
                    start=start,
                    end=start + WINDOW,
                    ignoring_appointment=ignoring,
                )
            ]

        shown = {p.id: p for p in app.search_providers.execute(SearchCriteria()).items}
        next_slots = shown[free.id].next_slots
        assert next_slots is not None
        assert list(next_slots.starts) == accepted(free.id)[:3]
        assert SLOT_START not in next_slots.starts
        week = app.view_provider_page.execute(
            provider_id=free.id, type_id=world.scene.kind, week=SLOT_START.date()
        )
        assert SLOT_START not in week.starts
        assert SLOT_START in accepted(other.id, ignoring=taken)

        refused = verify(app, world, free.id, SLOT_START)
        assert isinstance(refused, DomainError)
        assert refused.code is ErrorCode.NO_ROOM_AVAILABLE
        assert not isinstance(verify(app, world, free.id, next_slots.starts[0]), DomainError)


def verify(app: Container, world: Bookable, clinician: Id, at: datetime) -> object:
    created = app.create_hold.execute(
        appointment_type_id=world.scene.kind,
        clinician_id=clinician,
        start=at,
        **world.visitor(),  # type: ignore[arg-type]
    )
    return app.verify_hold.execute(
        hold_id=created.hold_id, code=world.code(), user_agent="test"
    ).outcome


def book(app: Container, world: Bookable, clinician: Id, at: datetime) -> Id:
    booked = verify(app, world, clinician, at)
    assert not isinstance(booked, DomainError)
    return booked.id  # type: ignore[attr-defined]
