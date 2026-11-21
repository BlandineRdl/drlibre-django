from drlibre.scheduling.application.ports.outbound import SlotStore, StoredSlot
from drlibre.scheduling.infrastructure.django.models import SlotModel
from drlibre.shared_kernel.ids import Id


class DjangoSlotStore(SlotStore):
    """One DELETE and one bulk INSERT per clinician, inside the caller's transaction."""

    def replace(self, clinician_id: Id, slots: tuple[StoredSlot, ...]) -> None:
        SlotModel.objects.filter(clinician_id=clinician_id.value).delete()
        SlotModel.objects.bulk_create(
            (
                SlotModel(
                    clinician_id=s.clinician_id.value,
                    appointment_type_id=s.appointment_type_id.value,
                    start=s.slot.start,
                    end=s.slot.end,
                )
                for s in slots
            ),
            batch_size=1000,
        )
