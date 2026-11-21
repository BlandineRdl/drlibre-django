from datetime import datetime

from drlibre.booking.application.ports.inbound import BookForPatient
from drlibre.booking.application.ports.outbound import BookingDirectory, Staff
from drlibre.booking.application.use_cases.actor_scope import ActorKind, actor_scope
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field


class BookForPatientUseCase(BookForPatient):
    def __init__(
        self, *, uow: UnitOfWork, directory: BookingDirectory, staff: Staff, placement: Placement
    ) -> None:
        self._uow = uow
        self._directory = directory
        self._staff = staff
        self._placement = placement

    def execute(
        self,
        *,
        actor_id: Id,
        patient_id: Id,
        appointment_type_id: Id,
        start: datetime,
        room_id: Id | None = None,
        clinician_id: Id | None = None,
    ) -> Appointment:
        with self._uow:
            if actor_scope(self._directory, self._staff, actor_id).kind is ActorKind.ADMIN:
                # An admin books in any clinician's agenda, named by them (spec 14).
                if clinician_id is None:
                    raise invalid_field("clinician", "Indiquez le praticien.")
                booked_with = clinician_id
            else:
                booked_with = clinician_profile(self._directory, actor_id)
                if clinician_id not in (None, booked_with):
                    raise DomainError(ErrorCode.FORBIDDEN, "Réservez dans votre propre agenda.")
            return self._placement.place(
                patient_id=patient_id,
                clinician_id=booked_with,
                appointment_type_id=appointment_type_id,
                start=start,
                source=Source.STAFF,
                for_patient=False,
                actor_id=actor_id,
                room_id=room_id,
            )
