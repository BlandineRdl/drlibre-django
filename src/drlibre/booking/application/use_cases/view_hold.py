from drlibre.booking.application.ports.inbound import HoldSummary, ViewHold
from drlibre.booking.application.ports.outbound import Holds
from drlibre.booking.domain.appointment import Source
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class ViewHoldUseCase(ViewHold):
    def __init__(self, *, clock: Clock, holds: Holds) -> None:
        self._clock = clock
        self._holds = holds

    def execute(self, *, hold_id: Id) -> HoldSummary:
        hold = self._holds.get(hold_id)
        if hold is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Réservation provisoire introuvable.")
        return HoldSummary(
            hold_id=hold.id,
            clinician_id=hold.clinician_id,
            appointment_type_id=hold.appointment_type_id,
            start=hold.start,
            end=hold.end,
            expires_at=hold.expires_at,
            open=hold.is_open(self._clock.now()),
            first_available=hold.source is Source.ROUND_ROBIN,
        )
