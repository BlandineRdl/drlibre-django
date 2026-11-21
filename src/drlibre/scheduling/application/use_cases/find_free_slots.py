from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import FindFreeSlots
from drlibre.scheduling.application.ports.outbound import SchedulingDirectory, SlotQueries
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

MAX_RANGE = timedelta(days=31)


class FindFreeSlotsUseCase(FindFreeSlots):
    def __init__(self, *, clock: Clock, directory: SchedulingDirectory, queries: SlotQueries):
        self._clock = clock
        self._directory = directory
        self._queries = queries

    def execute(
        self, *, appointment_type_id: Id, clinician_id: Id | None, start: datetime, end: datetime
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
        return self._queries.free_slots(
            kind.id, clinicians, within=within, not_before=self._clock.now()
        )


def _local_span(period: Period, tz: ZoneInfo) -> timedelta:
    # Wall-clock span in the hospital's zone, so a daylight saving change neither adds nor removes.
    local = (period.start.astimezone(tz), period.end.astimezone(tz))
    return local[1].replace(tzinfo=None) - local[0].replace(tzinfo=None)
