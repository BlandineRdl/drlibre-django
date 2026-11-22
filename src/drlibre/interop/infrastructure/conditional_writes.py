from collections.abc import Callable

from django.db import models, transaction

from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.interop.application.ports.inbound import (
    ConditionalWrites,
    Locked,
    StaleVersionError,
    WriteTarget,
)
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    ClinicianProfileRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel

# A lock adapter, like booking's schedule locks, may lock other contexts' rows by their models.
_MODELS: dict[Locked, type[models.Model]] = {
    Locked.CLINICIAN: ClinicianProfileRecord,
    Locked.USER: UserRecord,
    Locked.APPOINTMENT: AppointmentRecord,
    Locked.AVAILABILITY_RULE: AvailabilityRuleModel,
    Locked.HOSPITAL: HospitalRecord,
    Locked.DEPARTMENT: DepartmentRecord,
    Locked.ROOM: RoomRecord,
    Locked.APPOINTMENT_TYPE: AppointmentTypeRecord,
    Locked.SPECIALTY: SpecialtyRecord,
}


class DjangoConditionalWrites(ConditionalWrites):
    """One outer transaction: the write's unit of work nests in it as a savepoint."""

    def run[T](
        self,
        *,
        target: WriteTarget,
        expected: str | None,
        current: Callable[[], str],
        write: Callable[[], T],
    ) -> T:
        with transaction.atomic():
            for kind, row_id in target.rows:
                rows = _MODELS[kind].objects.select_for_update(no_key=True).filter(pk=row_id.value)
                list(rows.values_list("pk", flat=True))
            if expected is not None and current() != expected:
                raise StaleVersionError
            return write()
