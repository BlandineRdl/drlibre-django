from drlibre.booking.application.ports.inbound import AppointmentQueries
from drlibre.organisation.application.ports.outbound import ScheduleDependents
from drlibre.scheduling.application.ports.inbound import RoomUsage
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class ScheduleAndBookingDependents(ScheduleDependents):
    """Asks scheduling which rules use a room and booking which appointments use a record."""

    def __init__(self, *, usage: RoomUsage, appointments: AppointmentQueries) -> None:
        self._usage = usage
        self._appointments = appointments

    def for_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return self._usage.rules_using(room_id) + self._appointments.dependents_of_room(room_id)

    def for_appointment_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return self._appointments.dependents_of_type(appointment_type_id)

    def for_clinician_profile(self, profile_id: Id) -> tuple[Dependent, ...]:
        return self._appointments.dependents_of_clinician(profile_id)
