"""Behaviour properties of the spec 5.5 round robin ranking."""

import dataclasses
from datetime import UTC, datetime, timedelta
from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from drlibre.booking.domain.round_robin import Candidate, rank
from drlibre.shared_kernel.ids import Id

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)

assigned_at = st.none() | st.integers(1, 10_000).map(lambda m: NOW - timedelta(minutes=m))
candidates = st.lists(
    st.builds(
        Candidate,
        clinician_id=st.uuids().map(Id),
        weight=st.integers(1, 10),
        last_assigned_at=assigned_at,
    ),
    unique_by=lambda c: c.clinician_id,
    max_size=8,
)


def score(candidate: Candidate) -> timedelta:
    assert candidate.last_assigned_at is not None
    return (NOW - candidate.last_assigned_at) * candidate.weight


@given(candidates, st.randoms())
def test_ranking_is_total_and_ignores_input_order(pool: list[Candidate], rng) -> None:
    shuffled = list(pool)
    rng.shuffle(shuffled)
    assert rank(tuple(pool), NOW) == rank(tuple(shuffled), NOW)
    assert sorted(rank(tuple(pool), NOW), key=lambda c: c.clinician_id.value) == sorted(
        pool, key=lambda c: c.clinician_id.value
    )


@given(candidates)
def test_never_assigned_clinicians_come_first_by_lowest_id(pool: list[Candidate]) -> None:
    ranked = rank(tuple(pool), NOW)
    fresh = [c for c in ranked if c.last_assigned_at is None]
    assert ranked[: len(fresh)] == tuple(fresh)
    assert [c.clinician_id.value for c in fresh] == sorted(c.clinician_id.value for c in fresh)


@given(candidates)
def test_larger_elapsed_time_times_weight_comes_first_and_ties_go_to_lowest_id(
    pool: list[Candidate],
) -> None:
    assigned = [c for c in rank(tuple(pool), NOW) if c.last_assigned_at is not None]
    for first, second in pairwise(assigned):
        assert score(first) >= score(second)
        if score(first) == score(second):
            assert first.clinician_id.value < second.clinician_id.value


@given(candidates, st.integers(0, 7), st.integers(1, 10))
def test_a_larger_weight_never_ranks_a_clinician_later(
    pool: list[Candidate], index: int, extra: int
) -> None:
    if not pool:
        return
    target = pool[index % len(pool)]
    heavier = dataclasses.replace(target, weight=target.weight + extra)
    others = tuple(c for c in pool if c is not target)
    before = [c.clinician_id for c in rank((*others, target), NOW)].index(target.clinician_id)
    after = [c.clinician_id for c in rank((*others, heavier), NOW)].index(target.clinician_id)
    assert after <= before
