"""Behaviour properties of a waitlist entry's statuses and window (spec §3.1, §5.8)."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus, oldest
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
MINUTE = timedelta(minutes=1)
HALF_HOUR = timedelta(minutes=30)

offsets = st.integers(0, 60 * 24 * 30).map(lambda m: NOW + m * MINUTE)
lengths = st.integers(1, 60 * 24 * 30).map(lambda m: m * MINUTE)


def joined(earliest: datetime = NOW, length: timedelta = timedelta(days=7)) -> WaitlistEntry:
    return WaitlistEntry.join(
        patient_id=Id(),
        appointment_type_id=Id(),
        clinician_id=None,
        earliest=earliest,
        latest=earliest + length,
        at=NOW,
    )


def in_status(status: WaitlistStatus) -> WaitlistEntry:
    entry = joined()
    if status is WaitlistStatus.WAITING:
        return entry
    if status is WaitlistStatus.EXPIRED:
        return entry.expired()
    offered = entry.offered(Id())
    return offered if status is WaitlistStatus.OFFERED else offered.booked()


Move = Callable[[WaitlistEntry], WaitlistEntry]
MOVES: dict[str, tuple[Move, WaitlistStatus]] = {
    "offered": (lambda e: e.offered(Id()), WaitlistStatus.WAITING),
    "booked": (lambda e: e.booked(), WaitlistStatus.OFFERED),
    "back_to_waiting": (lambda e: e.back_to_waiting(), WaitlistStatus.OFFERED),
    "expired": (lambda e: e.expired(), WaitlistStatus.WAITING),
}


def test_an_entry_waits_is_offered_then_booked_and_the_offer_link_follows() -> None:
    """Règle §3.1 : WAITING, puis OFFERED sur le RDV libéré, puis BOOKED."""
    appointment = Id()
    entry = joined()
    offered = entry.offered(appointment)
    booked = offered.booked()

    assert (entry.status, entry.offered_appointment_id) == (WaitlistStatus.WAITING, None)
    assert (offered.status, offered.offered_appointment_id) == (
        WaitlistStatus.OFFERED,
        appointment,
    )
    assert (booked.status, booked.offered_appointment_id) == (WaitlistStatus.BOOKED, None)


def test_a_lost_offer_goes_back_to_waiting_without_its_link() -> None:
    back = joined().offered(Id()).back_to_waiting()
    assert (back.status, back.offered_appointment_id) == (WaitlistStatus.WAITING, None)


def test_a_waiting_entry_expires() -> None:
    assert joined().expired().status is WaitlistStatus.EXPIRED


@pytest.mark.parametrize("move", sorted(MOVES))
@pytest.mark.parametrize("status", list(WaitlistStatus))
def test_any_other_change_is_refused_with_the_current_status(
    move: str, status: WaitlistStatus
) -> None:
    change, allowed_from = MOVES[move]
    entry = in_status(status)
    if status is allowed_from:
        assert change(entry).status is not status
        return
    with pytest.raises(DomainError) as refused:
        change(entry)
    assert refused.value.code is ErrorCode.INVALID_TRANSITION
    assert refused.value.details == {"status": status.value}


@given(offsets, st.integers(-60 * 24 * 30, 0).map(lambda m: m * MINUTE))
def test_an_empty_window_is_refused_on_its_end_date(earliest: datetime, back: timedelta) -> None:
    with pytest.raises(DomainError) as refused:
        joined(earliest, back)
    assert refused.value.code is ErrorCode.INVALID_INPUT
    assert refused.value.details["fields"][0]["field"] == "to_date"


@given(offsets, lengths, offsets)
def test_a_slot_fits_exactly_when_it_lies_inside_the_window(
    earliest: datetime, length: timedelta, start: datetime
) -> None:
    entry = joined(earliest, length)
    end = start + HALF_HOUR
    assert entry.fits(start, end) is (earliest <= start and end <= earliest + length)


def test_the_window_includes_both_its_bounds_and_nothing_beyond() -> None:
    entry = joined(NOW, timedelta(days=1))
    latest = entry.latest
    assert entry.fits(NOW, NOW + HALF_HOUR)
    assert entry.fits(latest - HALF_HOUR, latest)
    assert not entry.fits(NOW - MINUTE, NOW - MINUTE + HALF_HOUR)
    assert not entry.fits(latest - HALF_HOUR + MINUTE, latest + MINUTE)


def test_a_slot_matches_its_type_and_preferred_clinician_or_any_when_none() -> None:
    kind, preferred, other = Id(), Id(), Id()
    anyone = WaitlistEntry.join(
        patient_id=Id(),
        appointment_type_id=kind,
        clinician_id=None,
        earliest=NOW,
        latest=NOW + timedelta(days=1),
        at=NOW,
    )
    picky = WaitlistEntry.join(
        patient_id=Id(),
        appointment_type_id=kind,
        clinician_id=preferred,
        earliest=NOW,
        latest=NOW + timedelta(days=1),
        at=NOW,
    )
    start, end = NOW + timedelta(hours=1), NOW + timedelta(hours=1) + HALF_HOUR
    assert anyone.matches(kind, other, start, end)
    assert picky.matches(kind, preferred, start, end)
    assert not picky.matches(kind, other, start, end)
    assert not anyone.matches(Id(), other, start, end)


@given(st.integers(-600, 600).map(lambda m: m * MINUTE))
def test_a_patient_accepts_an_offer_only_two_hours_or_more_ahead(ahead: timedelta) -> None:
    offered = joined().offered(Id())
    assert offered.acceptable_by_patient(NOW + ahead, NOW) is (ahead >= timedelta(hours=2))
    assert not joined().acceptable_by_patient(NOW + timedelta(days=1), NOW)


@given(st.lists(st.tuples(offsets, st.uuids()), min_size=1, max_size=8, unique_by=lambda t: t[1]))
def test_the_oldest_entry_is_the_first_joined_then_the_lowest_id(
    joins: list[tuple[datetime, uuid.UUID]],
) -> None:
    entries = [
        WaitlistEntry(
            id=Id(uid),
            patient_id=Id(),
            appointment_type_id=Id(),
            clinician_id=None,
            earliest=NOW,
            latest=NOW + timedelta(days=1),
            status=WaitlistStatus.WAITING,
            created_at=created,
        )
        for created, uid in joins
    ]
    first = oldest(entries)
    assert first is not None
    assert all((first.created_at, first.id.value) <= (e.created_at, e.id.value) for e in entries)
    assert oldest([]) is None
