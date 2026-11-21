from dataclasses import dataclass
from datetime import datetime, timedelta

from drlibre.shared_kernel.ids import Id

_MICROSECOND = timedelta(microseconds=1)


@dataclass(frozen=True, slots=True)
class Candidate:
    clinician_id: Id
    weight: int
    last_assigned_at: datetime | None


def rank(candidates: tuple[Candidate, ...], now: datetime) -> tuple[Candidate, ...]:
    """Never assigned first, then largest elapsed time times weight, ties to the lowest id."""

    def key(candidate: Candidate) -> tuple[int, int, int]:
        if candidate.last_assigned_at is None:
            return (0, 0, candidate.clinician_id.value.int)
        score = (now - candidate.last_assigned_at) // _MICROSECOND * candidate.weight
        return (1, -score, candidate.clinician_id.value.int)

    return tuple(sorted(candidates, key=key))
