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
from drlibre.organisation.infrastructure.django.models import ClinicianProfileRecord
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel
from drlibre.shared_kernel.errors import DomainError

# A lock adapter, like booking's schedule locks, may lock other contexts' rows by their models.
_MODELS: dict[Locked, type[models.Model]] = {
    Locked.CLINICIAN: ClinicianProfileRecord,
    Locked.USER: UserRecord,
    Locked.APPOINTMENT: AppointmentRecord,
    Locked.AVAILABILITY_RULE: AvailabilityRuleModel,
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
        if expected is None:
            return write()
        refused: DomainError | None = None
        with transaction.atomic():
            for kind, row_id in target.rows:
                rows = _MODELS[kind].objects.select_for_update().filter(pk=row_id.value)
                list(rows.values_list("pk", flat=True))
            if current() != expected:
                raise StaleVersionError
            try:
                return write()
            except DomainError as error:
                # A refusal after its own commit, such as a lapsed offer put back, keeps it.
                refused = error
        raise refused
