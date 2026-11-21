from drlibre.booking.application.ports.inbound import MarkNoShow
from drlibre.booking.application.use_cases.status_change import StatusChange
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id


class MarkNoShowUseCase(MarkNoShow):
    def __init__(self, *, change: StatusChange) -> None:
        self._change = change

    def execute(self, *, actor_id: Id, appointment_id: Id) -> Appointment:
        return self._change.apply(
            actor_id=actor_id, appointment_id=appointment_id, transition=Appointment.no_show
        )
