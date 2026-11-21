from drlibre.booking.application.ports.outbound import Appointments, BookingDirectory
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
