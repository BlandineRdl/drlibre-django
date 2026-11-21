from datetime import datetime, timedelta

from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    ClinicianSlot,
    SlotHolds,
    SlotQueries,
)
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
) -> tuple[ClinicianSlot, ...]:
    """Stored free slots minus those an open hold covers, the hold stretched by the type buffer."""
    stored = queries.free_slots(kind.id, clinicians, within=within, not_before=now)
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
