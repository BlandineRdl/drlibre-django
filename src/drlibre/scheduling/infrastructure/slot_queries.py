from datetime import datetime

from drlibre.scheduling.application.ports.outbound import ClinicianSlot, SlotQueries
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
    ) -> tuple[ClinicianSlot, ...]:
        rows = (
            SlotModel.objects.filter(
                appointment_type_id=appointment_type_id.value,
                clinician_id__in=[c.value for c in clinician_ids],
                start__gte=max(within.start, not_before),
                end__lte=within.end,
            )
            .order_by("start", "clinician_id")
            .values_list("clinician_id", "start", "end")
        )
        return tuple(
            ClinicianSlot(Id(clinician), Slot(start, end)) for clinician, start, end in rows
        )
