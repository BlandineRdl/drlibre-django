from drlibre.scheduling.application.ports.outbound import SlotStore, StoredSlot
from drlibre.scheduling.infrastructure.django.models import SlotModel
from drlibre.shared_kernel.ids import Id


class DjangoSlotStore(SlotStore):
    """Deletes a clinician's stale rows, inserts the missing ones, in the caller's transaction."""

    def replace(self, clinician_id: Id, slots: tuple[StoredSlot, ...]) -> None:
        rows = SlotModel.objects.filter(clinician_id=clinician_id.value)
        wanted = {_key(s) for s in slots}
        kept: set[tuple[object, ...]] = set()
        stale = []
        for pk, *key in rows.values_list("pk", "appointment_type_id", "start", "end"):
            if tuple(key) in wanted and tuple(key) not in kept:
                kept.add(tuple(key))
            else:
                stale.append(pk)
        if stale:
            rows.filter(pk__in=stale).delete()
        SlotModel.objects.bulk_create(
            (
                SlotModel(
                    clinician_id=s.clinician_id.value,
                    appointment_type_id=s.appointment_type_id.value,
                    start=s.slot.start,
                    end=s.slot.end,
                )
                for s in slots
                if _key(s) not in kept
            ),
            batch_size=1000,
        )


def _key(s: StoredSlot) -> tuple[object, ...]:
    return (s.appointment_type_id.value, s.slot.start, s.slot.end)
