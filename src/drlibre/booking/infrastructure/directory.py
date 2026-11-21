from drlibre.booking.application.ports.outbound import (
    BookableClinician,
    BookableType,
    BookingDirectory,
    Venue,
)
from drlibre.identity.application.ports.inbound import Role, StaffLookup
from drlibre.organisation.application.ports.inbound import ReferenceQueries
from drlibre.shared_kernel.ids import Id


class OrganisationBookingDirectory(BookingDirectory):
    """Reads types, profiles, rooms, hospitals from organisation, staff names from identity."""

    def __init__(self, *, queries: ReferenceQueries, staff: StaffLookup) -> None:
        self._queries = queries
        self._staff = staff

    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        kind = self._queries.appointment_type(appointment_type_id)
        department = self._queries.department(kind.department_id) if kind else None
        hospital = self._queries.hospital(department.hospital_id) if department else None
        if kind is None or hospital is None:
            return None
        return BookableType(
            id=kind.id,
            department_id=kind.department_id,
            duration_minutes=kind.duration_minutes,
            needs_room=kind.needs_room,
            bookable_online=kind.bookable_online,
            active=kind.active,
            time_zone=hospital.time_zone,
        )

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        profile = self._queries.clinician_profile(clinician_id)
        if profile is None:
            return None
        member = self._staff.staff_member(profile.user_id)
        return BookableClinician(
            id=profile.id,
            department_id=profile.department_id,
            active=member is not None and member.active and member.role is Role.CLINICIAN,
            default_room_id=profile.default_room_id,
            weight=profile.weight,
            last_assigned_at=profile.last_assigned_at,
        )

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        rooms = sorted(
            (r for r in self._queries.department_rooms(department_id) if r.active),
            key=lambda r: r.code,
        )
        return tuple(r.id for r in rooms)

    def venue(self, clinician_id: Id) -> Venue | None:
        profile = self._queries.clinician_profile(clinician_id)
        department = self._queries.department(profile.department_id) if profile else None
        hospital = self._queries.hospital(department.hospital_id) if department else None
        member = self._staff.staff_member(profile.user_id) if profile else None
        if hospital is None or member is None:
            return None
        return Venue(
            hospital_name=hospital.name,
            time_zone=hospital.time_zone,
            provider_name=member.full_name,
        )
