from drlibre.organisation.application.ports.outbound import ScheduleDependents
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class NoScheduleYet(ScheduleDependents):
    """Null adapter until scheduling, booking and waitlist model what uses rooms and types."""

    def for_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return ()

    def for_appointment_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return ()

    def for_clinician_profile(self, profile_id: Id) -> tuple[Dependent, ...]:
        return ()
