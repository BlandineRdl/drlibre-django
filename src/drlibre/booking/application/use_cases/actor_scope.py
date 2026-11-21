from dataclasses import dataclass
from enum import StrEnum

from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingDirectory,
    ScheduleLocks,
    Staff,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import (
    own_clinician_appointment,
)
from drlibre.booking.application.use_cases.view_appointment import own_appointment
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

STAFF_ONLY = "Réservé au personnel."


class ActorKind(StrEnum):
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"
    ADMIN = "ADMIN"


@dataclass(frozen=True, slots=True)
class ActorScope:
    """Who acts on an appointment: a patient, a clinician by their profile, or an admin."""

    kind: ActorKind
    actor_id: Id
    profile_id: Id | None = None

    @property
    def is_patient(self) -> bool:
        return self.kind is ActorKind.PATIENT

    def require_staff(self) -> None:
        """forbidden for a patient."""
        if self.is_patient:
            raise DomainError(ErrorCode.FORBIDDEN, STAFF_ONLY)


def actor_scope(directory: BookingDirectory, staff: Staff, actor_id: Id) -> ActorScope:
    """A clinician profile makes a clinician, an active admin an admin, anyone else a patient."""
    profile_id = directory.clinician_of_user(actor_id)
    if profile_id is not None:
        return ActorScope(ActorKind.CLINICIAN, actor_id, profile_id)
    if staff.is_admin(actor_id):
        return ActorScope(ActorKind.ADMIN, actor_id)
    return ActorScope(ActorKind.PATIENT, actor_id)


def scoped_appointment(
    scope: ActorScope, appointments: Appointments, appointment_id: Id
) -> Appointment:
    """Any appointment for an admin, else the actor's own; not_found when absent."""
    if scope.kind is ActorKind.ADMIN:
        appointment = appointments.get(appointment_id)
        if appointment is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
        return appointment
    if scope.profile_id is not None:
        return own_clinician_appointment(appointments, appointment_id, scope.profile_id)
    return own_appointment(appointments, appointment_id, scope.actor_id)


def locked_scoped_appointment(
    scope: ActorScope, appointments: Appointments, locks: ScheduleLocks, appointment_id: Id
) -> Appointment:
    """The scoped appointment read again under the clinician then patient locks."""
    found = scoped_appointment(scope, appointments, appointment_id)
    locks.lock_clinician(found.clinician_id)
    locks.lock_patient(found.patient_id)
    return scoped_appointment(scope, appointments, appointment_id)
