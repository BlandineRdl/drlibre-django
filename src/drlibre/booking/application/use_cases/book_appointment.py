from datetime import datetime

from drlibre.booking.application.ports.inbound import BookAppointment
from drlibre.booking.application.ports.outbound import (
    BookingDirectory,
    FreeSlots,
    RoundRobinLedger,
)
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.booking.domain.round_robin import Candidate, rank
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class BookAppointmentUseCase(BookAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        placement: Placement,
        directory: BookingDirectory,
        free_slots: FreeSlots,
        ledger: RoundRobinLedger,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._placement = placement
        self._directory = directory
        self._free_slots = free_slots
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
            chosen = self._first_available(appointment_type_id, start)
            appointment = self._placement.place(
                patient_id=patient_id,
                clinician_id=chosen,
                appointment_type_id=appointment_type_id,
                start=start,
                source=Source.ROUND_ROBIN,
            )
            self._ledger.record(chosen, self._clock.now())
            return appointment

    def _first_available(self, appointment_type_id: Id, start: datetime) -> Id:
        kind = self._placement.bookable_type(appointment_type_id)
        candidates = []
        for clinician_id in self._free_slots.candidates_at(kind.id, start):
            clinician = self._directory.clinician(clinician_id)
            if (
                clinician is not None
                and clinician.active
                and clinician.department_id == kind.department_id
                and clinician.weight > 0
            ):
                candidates.append(
                    Candidate(clinician.id, clinician.weight, clinician.last_assigned_at)
                )
        ranked = rank(tuple(candidates), self._clock.now())
        if not ranked:
            raise DomainError(ErrorCode.NO_CLINICIAN_AVAILABLE, "Aucun praticien disponible.")
        return ranked[0].clinician_id
