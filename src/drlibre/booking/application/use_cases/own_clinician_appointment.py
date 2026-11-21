from drlibre.booking.application.ports.outbound import Appointments, BookingDirectory, ScheduleLocks
from drlibre.booking.application.use_cases.view_appointment import own_appointment
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

CLINICIANS_ONLY = "Réservé aux praticiens ayant un profil."


def clinician_profile(directory: BookingDirectory, user_id: Id) -> Id:
    """The user's clinician profile; forbidden when the user holds none."""
    profile_id = directory.clinician_of_user(user_id)
    if profile_id is None:
        raise DomainError(ErrorCode.FORBIDDEN, CLINICIANS_ONLY)
    return profile_id


def own_clinician_appointment(
    appointments: Appointments, appointment_id: Id, profile_id: Id
) -> Appointment:
    """The clinician's own appointment; not_found when absent, forbidden for another clinician."""
    appointment = appointments.get(appointment_id)
    if appointment is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
    if appointment.clinician_id != profile_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Ce rendez-vous n'est pas le vôtre.")
    return appointment


def locked_clinician_appointment(
    *,
    directory: BookingDirectory,
    appointments: Appointments,
    locks: ScheduleLocks,
    actor_id: Id,
    appointment_id: Id,
) -> Appointment:
    """The actor's own appointment read again under the clinician then patient locks."""
    profile_id = clinician_profile(directory, actor_id)
    found = own_clinician_appointment(appointments, appointment_id, profile_id)
    locks.lock_clinician(found.clinician_id)
    locks.lock_patient(found.patient_id)
    return own_clinician_appointment(appointments, appointment_id, profile_id)


def own_appointment_of(
    appointments: Appointments, appointment_id: Id, actor_id: Id, profile_id: Id | None
) -> Appointment:
    """The clinician's own appointment when a profile is given, else the patient's own."""
    if profile_id is None:
        return own_appointment(appointments, appointment_id, actor_id)
    return own_clinician_appointment(appointments, appointment_id, profile_id)
