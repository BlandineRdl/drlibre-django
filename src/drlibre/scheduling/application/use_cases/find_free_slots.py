from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import FindFreeSlots
from drlibre.scheduling.application.ports.outbound import (
    SchedulingDirectory,
    SlotHolds,
    SlotQueries,
)
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation
from drlibre.scheduling.application.use_cases.open_slots import computed_without, open_slots
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

MAX_RANGE = timedelta(days=31)


class FindFreeSlotsUseCase(FindFreeSlots):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: SchedulingDirectory,
        queries: SlotQueries,
        holds: SlotHolds,
        computation: SlotComputation,
    ):
        self._clock = clock
        self._directory = directory
        self._queries = queries
        self._holds = holds
        self._computation = computation

    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        end: datetime,
        ignoring_appointment: Id | None = None,
    ) -> tuple[Slot, ...]:
        within = Period(start, end)
        kind = self._directory.appointment_type(appointment_type_id)
        if kind is None or not kind.active:
            raise DomainError(ErrorCode.NOT_FOUND, "Type de RDV introuvable.")
        if _local_span(within, ZoneInfo(kind.time_zone)) > MAX_RANGE:
            raise invalid_field("end", "La période couvre 31 jours au plus.")
        if clinician_id is None:
            clinicians = self._directory.active_clinicians(kind.department_id)
        else:
            clinician = self._directory.clinician(clinician_id)
            if (
                clinician is None
                or not clinician.active
                or clinician.department_id != kind.department_id
            ):
                raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
            clinicians = (clinician.id,)
        now = self._clock.now()
        found = open_slots(
            queries=self._queries,
            holds=self._holds,
            kind=kind,
            clinicians=clinicians,
            within=within,
            now=now,
            computed=computed_without(
                self._computation, ignoring_appointment, kind, clinicians, within, now
            ),
        )
        by_start = {s.slot.start: s.slot for s in found}
        return tuple(by_start[at] for at in sorted(by_start))


def _local_span(period: Period, tz: ZoneInfo) -> timedelta:
    # Wall-clock span in the hospital's zone, so a daylight saving change neither adds nor removes.
    local = (period.start.astimezone(tz), period.end.astimezone(tz))
    return local[1].replace(tzinfo=None) - local[0].replace(tzinfo=None)
