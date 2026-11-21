from datetime import datetime

from drlibre.booking.application.ports.inbound import BookAppointment
from drlibre.booking.application.ports.outbound import (
    RoundRobinLedger,
)
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class BookAppointmentUseCase(BookAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        placement: Placement,
        ledger: RoundRobinLedger,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._placement = placement
        self._ledger = ledger

    def execute(
        self,
        *,
        patient_id: Id,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
    ) -> Appointment:
        with self._uow:
            if clinician_id is not None:
                return self._placement.place(
                    patient_id=patient_id,
                    clinician_id=clinician_id,
                    appointment_type_id=appointment_type_id,
                    start=start,
                    source=Source.ONLINE,
                )
            kind = self._placement.bookable_type(appointment_type_id)

            def attempt(chosen: Id) -> Appointment:
                appointment = self._placement.place(
                    patient_id=patient_id,
                    clinician_id=chosen,
                    appointment_type_id=appointment_type_id,
                    start=start,
                    source=Source.ROUND_ROBIN,
                )
                self._ledger.record(chosen, self._clock.now())
                return appointment

            return self._placement.first_free(
                self._placement.ranked_candidates(kind, start), attempt
            )
