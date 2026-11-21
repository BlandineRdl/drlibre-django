from drlibre.booking.application.ports.inbound import CompleteAppointment
from drlibre.booking.application.use_cases.status_change import StatusChange
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.ids import Id


class CompleteAppointmentUseCase(CompleteAppointment):
    def __init__(self, *, change: StatusChange) -> None:
        self._change = change

    def execute(self, *, actor_id: Id, appointment_id: Id) -> Appointment:
        return self._change.apply(
            actor_id=actor_id, appointment_id=appointment_id, transition=Appointment.completed
        )
