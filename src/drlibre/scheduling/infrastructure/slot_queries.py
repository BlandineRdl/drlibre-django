from datetime import datetime

from drlibre.scheduling.application.ports.outbound import SlotQueries
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.infrastructure.django.models import SlotModel
from drlibre.shared_kernel.ids import Id


class DjangoSlotQueries(SlotQueries):
    """Reads the precomputed table only; the caller passes the active clinicians."""

    def free_slots(
        self,
        appointment_type_id: Id,
        clinician_ids: tuple[Id, ...],
        *,
        within: Period,
        not_before: datetime,
    ) -> tuple[Slot, ...]:
        rows = (
            SlotModel.objects.filter(
                appointment_type_id=appointment_type_id.value,
                clinician_id__in=[c.value for c in clinician_ids],
                start__gte=max(within.start, not_before),
                end__lte=within.end,
            )
            .order_by("start")
            .distinct("start")
            .values_list("start", "end")
        )
        return tuple(Slot(start, end) for start, end in rows)
