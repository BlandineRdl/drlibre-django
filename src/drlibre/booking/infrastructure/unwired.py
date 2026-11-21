from datetime import datetime

from drlibre.booking.application.ports.inbound import (
    BookAppointment,
    CreateHold,
    ExpireHolds,
    HeldPeriod,
    HoldCreated,
    OpenHolds,
    ResendCode,
    VerifiedBooking,
    VerifyHold,
)
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id

_MESSAGE = "Booking adapters are not wired yet."


class UnwiredBookAppointment(BookAppointment):
    """Stands in until the Django booking adapters exist (E3 phase 3); nothing exposes it yet."""

    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        raise NotImplementedError(_MESSAGE)


class UnwiredCreateHold(CreateHold):
    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        full_name: str,
        birth_date: str,
        email: str,
        phone: str,
        reason: str,
        accepted_terms: bool,
        network: str,
    ) -> HoldCreated:
        raise NotImplementedError(_MESSAGE)


class UnwiredVerifyHold(VerifyHold):
    def execute(self, *, hold_id: Id, code: str, user_agent: str) -> VerifiedBooking:
        raise NotImplementedError(_MESSAGE)


class UnwiredResendCode(ResendCode):
    def execute(self, *, hold_id: Id, network: str) -> None:
        raise NotImplementedError(_MESSAGE)


class UnwiredExpireHolds(ExpireHolds):
    def execute(self) -> int:
        raise NotImplementedError(_MESSAGE)


class UnwiredOpenHolds(OpenHolds):
    def execute(
        self, *, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, at: datetime
    ) -> tuple[HeldPeriod, ...]:
        raise NotImplementedError(_MESSAGE)
