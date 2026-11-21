from datetime import datetime, timedelta

from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    ClinicianSlot,
    SlotHolds,
    SlotQueries,
)
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation
from drlibre.scheduling.domain.slot import Period
from drlibre.shared_kernel.ids import Id


def open_slots(
    *,
    queries: SlotQueries,
    holds: SlotHolds,
    kind: AppointmentType,
    clinicians: tuple[Id, ...],
    within: Period,
    now: datetime,
    ignoring_hold: Id | None = None,
    computed: tuple[ClinicianSlot, ...] | None = None,
) -> tuple[ClinicianSlot, ...]:
    """Free slots, stored unless computed given, minus those an open hold covers plus buffer."""
    stored = (
        queries.free_slots(kind.id, clinicians, within=within, not_before=now)
        if computed is None
        else computed
    )
    if not stored:
        return ()
    buffer = timedelta(minutes=kind.buffer_minutes)
    held = holds.open(
        clinicians,
        within=Period(within.start - buffer, within.end),
        at=now,
        ignoring=ignoring_hold,
    )
    return tuple(
        found
        for found in stored
        if not any(
            h.clinician_id == found.clinician_id
            and found.slot.period.overlaps(h.period.extended(buffer))
            for h in held
        )
    )


def clinicians_free_at(
    *,
    queries: SlotQueries,
    holds: SlotHolds,
    kind: AppointmentType,
    clinicians: tuple[Id, ...],
    start: datetime,
    now: datetime,
    ignoring_hold: Id | None = None,
    computation: SlotComputation | None = None,
    ignoring_appointment: Id | None = None,
) -> tuple[Id, ...]:
    """The clinicians with an open slot of the type starting exactly at the start."""
    within = Period(start, start + timedelta(minutes=kind.duration_minutes))
    slots = open_slots(
        queries=queries,
        holds=holds,
        kind=kind,
        clinicians=clinicians,
        within=within,
        now=now,
        ignoring_hold=ignoring_hold,
        computed=computed_without(computation, ignoring_appointment, kind, clinicians, within, now),
    )
    return tuple(dict.fromkeys(s.clinician_id for s in slots if s.slot.start == start))


def computed_without(
    computation: SlotComputation | None,
    appointment_id: Id | None,
    kind: AppointmentType,
    clinicians: tuple[Id, ...],
    within: Period,
    now: datetime,
) -> tuple[ClinicianSlot, ...] | None:
    """Slots recomputed without the appointment, or None to read the stored table."""
    if computation is None or appointment_id is None:
        return None
    return computation.ignoring(
        appointment_id, kind=kind, clinicians=clinicians, within=within, now=now
    )
