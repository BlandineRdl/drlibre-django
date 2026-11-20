from drlibre.organisation.application.ports.outbound import Departments, Rooms, Specialties
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.validation import FieldErrors


def check_references(
    profile: ClinicianProfile, *, departments: Departments, specialties: Specialties, rooms: Rooms
) -> None:
    """Department and specialty exist; the default room is an active room of that department."""
    errors = FieldErrors()
    if departments.get(profile.department_id) is None:
        errors.add("department_id", "Choisissez un département.")
    specialty = specialties.get(profile.specialty_id)
    if specialty is None or not specialty.active:
        errors.add("specialty_id", "Choisissez une spécialité active.")
    if profile.default_room_id is not None:
        room = rooms.get(profile.default_room_id)
        if room is None or not room.active or room.department_id != profile.department_id:
            errors.add("default_room_id", "Choisissez une salle active de ce département.")
    errors.raise_if_any()


def as_dependents(profiles: tuple[ClinicianProfile, ...]) -> tuple[Dependent, ...]:
    return tuple(Dependent("clinician", p.id, p.label) for p in profiles)
