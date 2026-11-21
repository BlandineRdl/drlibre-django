import hashlib

from django.db import connection

from drlibre.booking.application.ports.outbound import ScheduleLocks
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import ClinicianProfileRecord, RoomRecord
from drlibre.shared_kernel.ids import Id


class DjangoScheduleLocks(ScheduleLocks):
    """Row locks held until the caller's transaction ends; an unknown id locks nothing."""

    def lock_email(self, email: str) -> None:
        digest = hashlib.blake2b(email.lower().encode(), digest_size=8).digest()
        key = int.from_bytes(digest, "big", signed=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])

    def lock_clinician(self, clinician_id: Id) -> None:
        rows = ClinicianProfileRecord.objects.select_for_update().filter(pk=clinician_id.value)
        list(rows.values_list("pk", flat=True))

    def lock_clinicians(self, clinician_ids: tuple[Id, ...]) -> None:
        rows = ClinicianProfileRecord.objects.select_for_update().filter(
            pk__in=[clinician_id.value for clinician_id in clinician_ids]
        )
        list(rows.order_by("pk").values_list("pk", flat=True))

    def lock_patient(self, patient_id: Id) -> None:
        rows = UserRecord.objects.select_for_update().filter(pk=patient_id.value)
        list(rows.values_list("pk", flat=True))

    def lock_rooms(self, department_id: Id) -> None:
        rows = RoomRecord.objects.select_for_update().filter(
            department_id=department_id.value, active=True
        )
        list(rows.order_by("pk").values_list("pk", flat=True))
