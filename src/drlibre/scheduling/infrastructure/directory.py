from drlibre.identity.application.ports.inbound import Role, StaffLookup
from drlibre.organisation.application.ports.inbound import AppointmentType as OrganisationType
from drlibre.organisation.application.ports.inbound import ClinicianProfile, ReferenceQueries
from drlibre.scheduling.application.ports.outbound import (
    AppointmentType,
    Clinician,
    Room,
    SchedulingDirectory,
)
from drlibre.shared_kernel.ids import Id


class OrganisationSchedulingDirectory(SchedulingDirectory):
    """Reads profiles, hospitals and types from organisation, staff activity from identity."""

    def __init__(self, *, queries: ReferenceQueries, lookup: StaffLookup) -> None:
        self._queries = queries
        self._lookup = lookup

    def clinician(self, clinician_id: Id) -> Clinician | None:
        profile = self._queries.clinician_profile(clinician_id)
        return self._clinician(profile) if profile else None

    def clinician_of(self, user_id: Id) -> Clinician | None:
        profile = self._queries.clinician_profile_of(user_id)
        return self._clinician(profile) if profile else None

    def active_clinicians(self, department_id: Id) -> tuple[Id, ...]:
        active = {member.user_id for member in self._lookup.active_clinicians()}
        profiles = self._queries.department_clinician_profiles(department_id)
        return tuple(p.id for p in profiles if p.user_id in active)

    def appointment_type(self, appointment_type_id: Id) -> AppointmentType | None:
        kind = self._queries.appointment_type(appointment_type_id)
        return _type(kind) if kind else None

    def appointment_types(self, department_id: Id) -> tuple[AppointmentType, ...]:
        return tuple(map(_type, self._queries.department_appointment_types(department_id)))

    def room(self, room_id: Id) -> Room | None:
        room = self._queries.room(room_id)
        return Room(room.id, room.department_id, room.active) if room else None

    def _clinician(self, profile: ClinicianProfile) -> Clinician | None:
        department = self._queries.department(profile.department_id)
        hospital = self._queries.hospital(department.hospital_id) if department else None
        if hospital is None:
            return None
        member = self._lookup.staff_member(profile.user_id)
        active = member is not None and member.active and member.role is Role.CLINICIAN
        return Clinician(profile.id, profile.department_id, hospital.time_zone, active)


def _type(kind: OrganisationType) -> AppointmentType:
    return AppointmentType(
        kind.id, kind.department_id, kind.duration_minutes, kind.buffer_minutes, kind.active
    )
