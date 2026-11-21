from drlibre.booking.application.ports.outbound import ScheduleLocks
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import ClinicianProfileRecord
from drlibre.shared_kernel.ids import Id


class DjangoScheduleLocks(ScheduleLocks):
    """Row locks held until the caller's transaction ends; an unknown id locks nothing."""

    def lock_clinician(self, clinician_id: Id) -> None:
        rows = ClinicianProfileRecord.objects.select_for_update().filter(pk=clinician_id.value)
        list(rows.values_list("pk", flat=True))

    def lock_patient(self, patient_id: Id) -> None:
        rows = UserRecord.objects.select_for_update().filter(pk=patient_id.value)
        list(rows.values_list("pk", flat=True))
