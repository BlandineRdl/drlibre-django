from drlibre.organisation.application.ports.outbound import ScheduleDependents
from drlibre.scheduling.application.ports.inbound import RoomUsage
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class SchedulingScheduleDependents(ScheduleDependents):
    """Asks scheduling, through its inbound port, which rules use a room; appointments in E3."""

    def __init__(self, *, usage: RoomUsage) -> None:
        self._usage = usage

    def for_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return self._usage.rules_using(room_id)

    def for_appointment_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return ()

    def for_clinician_profile(self, profile_id: Id) -> tuple[Dependent, ...]:
        return ()
